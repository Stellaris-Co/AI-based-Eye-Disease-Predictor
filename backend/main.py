from fastapi import FastAPI, File, UploadFile, Form, Response, HTTPException, Request, Depends, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import torch
from torchvision import models, transforms
from PIL import Image
import io
import uvicorn
import torch.nn as nn
import os
import numpy as np
import base64
import sys
import gc
import warnings
from datetime import datetime, timezone
from contextlib import asynccontextmanager
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from medical_data import MEDICAL_INFO

from sqlalchemy.orm import Session

from logging_config import configure_logging, get_logger
from db import create_tables, get_db, User, ScanResult, ClinicianOverride, AuditLog, ModelVersion
from audit import log_event
from auth import (
    hash_password, verify_password, create_access_token, decode_token,
    get_current_user, require_role, authenticate_user,
    SECRET_KEY as JWT_SECRET_KEY, ROLE_HIERARCHY,
)
from calibration import CalibrationRegistry, apply_temperature
from uncertainty import mc_dropout_predict, needs_human_review, build_review_payload
from iqa import assess_image_quality
from clinical_codes import get_clinical_code, CLINICAL_CODES
import model_registry
import storage

configure_logging(json_output=os.getenv("LOG_FORMAT", "json").lower() == "json")
logger = get_logger("ophthalmoai")
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
MODELS_DIR = os.getenv("MODELS_DIR", os.path.join(project_root, "models"))
FORCE_CPU = os.getenv("FORCE_CPU", "false").lower() in {"1", "true", "yes"}
DEVICE = torch.device("cuda" if torch.cuda.is_available() and not FORCE_CPU else "cpu")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_BYTES", str(20 * 1024 * 1024)))
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp", "image/jpg"}

ENVIRONMENT = os.getenv("ENVIRONMENT", "development").strip().lower()
CALIBRATION_PATH = os.path.join(MODELS_DIR, "calibration.json")
CALIBRATION_REGISTRY = CalibrationRegistry(CALIBRATION_PATH)
MC_DROPOUT_PASSES = int(os.getenv("MC_DROPOUT_PASSES", "8"))
ENABLE_UNCERTAINTY = os.getenv("ENABLE_UNCERTAINTY", "true").lower() in {"1", "true", "yes"}
ENABLE_IQA = os.getenv("ENABLE_IQA", "true").lower() in {"1", "true", "yes"}
PERSIST_SCANS = os.getenv("PERSIST_SCANS", "true").lower() in {"1", "true", "yes"}
GROUP_KEY_BY_IDX = {0: "eyelid", 1: "anterior", 2: "surface"}

HIERARCHY = {
    0: {'name': 'Adnexal Oculoplastic', 'model_file': 'specialist_eyelid.pth', 'classes': ['Eyelid']},
    1: {'name': 'Anterior Segment Pathology', 'model_file': 'specialist_anterior.pth', 'classes': ['Cataract', 'Uveitis']},
    2: {'name': 'Ocular Surface Disorders', 'model_file': 'specialist_surface.pth', 'classes': ['Conjunctivitis', 'Jaundice', 'Normal', 'Pterygium']}
}
ROUTER_MODEL = None
SPECIALIST_MODELS = {}
VISION_MODEL_KEYWORDS = ['llava', 'moondream', 'bakllava', 'vision', 'llava-phi3', 'minicpm-v']
OPHTHALMOLOGY_SYSTEM_PROMPT = """You are OphthalmoAI Doctor, a specialized AI medical assistant focused on ophthalmology and eye health education.

Your expertise covers:
- Cataract: Crystalline lens opacification, phacoemulsification, IOL implantation, visual rehabilitation
- Conjunctivitis (Pink Eye): Viral, bacterial, and allergic types; hygiene, antibiotic vs supportive care
- Uveitis: Uveal tract inflammation, autoimmune associations (RA, lupus), steroid therapy, urgency
- Eyelid Conditions: Stye (Hordeolum), Chalazion, Blepharitis; warm compresses, lid hygiene
- Jaundice / Scleral Icterus: Hyperbilirubinemia warning signs, liver/gallbladder implications
- Pterygium: UV-related fibrovascular growth, surgical excision, conjunctival autograft, UV protection
- Normal Eye Health: 20-20-20 rule, nutrition (lutein, omega-3, Vit A), UV protection, screening schedules

Response Guidelines:
1. Be warm, empathetic, and use accessible language — explain medical terms when used
2. For urgent red flags (sudden vision loss, chemical exposure, severe unilateral pain, trauma), immediately direct to emergency care
3. Always recommend professional ophthalmologist consultation for diagnosis and treatment
4. Provide practical, evidence-based prevention and self-care tips
5. DO NOT recommend specific prescription medications or dosages — general categories are okay
6. If a diagnosis context is provided, reference it as an "AI screening result" and discuss it appropriately
7. Keep responses focused, structured, and actionable — use bullet points where helpful
8. Acknowledge uncertainty honestly — say "this may suggest..." rather than definitive claims

You help patients understand conditions, navigate their options, and make informed decisions about seeking care."""

def build_router():
    model = models.mobilenet_v3_large(weights=None)
    model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, len(HIERARCHY))
    return model

def build_specialist(num_classes):
    model = models.efficientnet_b4(weights=None)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, num_classes)
    return model
preprocess = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

@asynccontextmanager
async def lifespan(app: FastAPI):
    global ROUTER_MODEL, SPECIALIST_MODELS
    logger.info("startup.begin", device=str(DEVICE), environment=ENVIRONMENT)
    print(f"🚀 Loading AI System onto {DEVICE}...")

    if ENVIRONMENT not in {"development", "dev", "test", "testing"} and \
            JWT_SECRET_KEY == "CHANGE_ME_BEFORE_PRODUCTION_DEPLOYMENT":
        raise RuntimeError(
            "JWT_SECRET_KEY is still the default placeholder value while "
            "ENVIRONMENT is not 'development'. Set a strong, random JWT_SECRET_KEY "
            "before deploying outside local development. See PRODUCTION.md."
        )

    try:
        create_tables()
        logger.info("startup.db_ready")
    except Exception as e:
        logger.error("startup.db_failed", error=str(e))
        print(f"⚠️  Database initialization failed: {e}. "
              f"Auth, scan history, and audit logging will not work until this is fixed.")

    if CALIBRATION_REGISTRY.all():
        logger.info("startup.calibration_loaded", temperatures=CALIBRATION_REGISTRY.all())
    else:
        logger.warning(
            "startup.calibration_missing",
            message="No calibration.json found — confidence scores are uncalibrated. "
                    "Run scripts/calibrate_models.py after training.",
        )

    router = build_router()
    router_path = os.path.join(MODELS_DIR, 'router.pth')
    if os.path.exists(router_path):
        try:
            router.load_state_dict(
                torch.load(router_path, map_location=DEVICE, weights_only=True),
                strict=False
            )
            router.to(DEVICE).eval()
            ROUTER_MODEL = router
            print("✅ Router (MobileNetV3) Loaded.")
        except Exception as e:
            print(f"❌ Router Load Failure: {e}")
    else:
        print(f"⚠️  Router model not found at {router_path}.")
        print(f"    Train it first with: python scripts/train_router.py")
    for idx, info in HIERARCHY.items():
        classes = info['classes']
        model_path = os.path.join(MODELS_DIR, info['model_file'])
        if len(classes) <= 1:
            SPECIALIST_MODELS[idx] = {
                'type': 'direct',
                'class': classes[0],
                'group_name': info['name']
            }
            print(f"✅ Specialist ({info['name']}): Direct pass-through.")
            continue
        model = build_specialist(len(classes))
        if os.path.exists(model_path):
            try:
                model.load_state_dict(
                    torch.load(model_path, map_location=DEVICE, weights_only=True)
                )
                model.to(DEVICE).eval()
                SPECIALIST_MODELS[idx] = {
                    'type': 'model',
                    'model': model,
                    'classes': classes,
                    'group_name': info['name']
                }
                print(f"✅ Specialist ({info['name']}) Loaded.")
            except Exception as e:
                print(f"❌ Specialist Load Failure for {info['name']}: {e}")
        else:
            print(f"⚠️  Specialist Model Missing: {info['model_file']}")
    yield
    logger.info("shutdown.begin")
    print("👋 Shutting down AI System.")
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()

app = FastAPI(lifespan=lifespan, title="OphthalmoAI API", version="2.0.0")

_cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
cors_origins = [origin.strip() for origin in _cors_origins_raw.split(",") if origin.strip()]
_is_wildcard = cors_origins == ["*"]
_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in {"1", "true", "yes"}

if _is_wildcard and _allow_credentials:
    raise RuntimeError(
        "Invalid CORS configuration: CORS_ORIGINS=* cannot be combined with "
        "CORS_ALLOW_CREDENTIALS=true. Set an explicit comma-separated origin list in "
        "CORS_ORIGINS, or leave CORS_ALLOW_CREDENTIALS unset/false."
    )

if _is_wildcard:
    warnings.warn(
        "CORS_ORIGINS=* is set. This is fine for local development but must be replaced "
        "with explicit origins before deploying publicly. See PRODUCTION.md.",
        stacklevel=1,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    PREDICT_RATE_LIMIT = os.getenv("PREDICT_RATE_LIMIT", "10/minute")
    CHAT_RATE_LIMIT = os.getenv("CHAT_RATE_LIMIT", "30/minute")
else:
    limiter = None
    warnings.warn(
        "slowapi is not installed — /predict and /chat are NOT rate limited. "
        "Install slowapi (see backend/requirements.txt) before any public deployment.",
        stacklevel=1,
    )


def _rate_limited(limit_string):
    """No-op decorator factory when slowapi isn't installed, so endpoint signatures
    don't need to branch on SLOWAPI_AVAILABLE."""
    if limiter is None:
        def _decorator(func):
            return func
        return _decorator
    return limiter.limit(limit_string)


class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    diagnosis_context: Optional[Dict[str, Any]] = None


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: Optional[str] = None
    role: str = "patient" 


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str
    user_id: str


class OverrideRequest(BaseModel):
    verdict: str  
    corrected_diagnosis: Optional[str] = None
    corrected_icd10: Optional[str] = None
    notes: Optional[str] = None


class ActivateModelRequest(BaseModel):
    version_id: str


_SEVERITY_ICON = {"info": "✅", "warning": "⚠️", "urgent": "🚨"}


def _build_symptom_alerts(
    diagnosis: str,
    pain_level: str,
    vision_loss: str,
    itchiness: str,
    halos: str = "No",
    discharge: str = "None",
    light_sensitivity: str = "No",
    floaters: str = "No",
    duration: str = "Not Sure",
):
    alerts = []  
    if diagnosis == "Conjunctivitis" and pain_level == "Severe":
        alerts.append(("warning", "Pain Mismatch: Severe pain is unusual for Pink Eye. Rule out Glaucoma or Keratitis."))
    if vision_loss == "Yes" and diagnosis in ["Conjunctivitis", "Eyelid"]:
        alerts.append(("warning", "Vision Loss Warning: Surface/Eyelid conditions rarely affect vision. Consider Keratitis or Uveitis."))
    if itchiness == "Yes" and diagnosis == "Conjunctivitis":
        alerts.append(("info", "Symptom Match: Itchiness strongly supports Allergic Conjunctivitis."))
    if diagnosis == "Jaundice":
        alerts.append(("urgent", "URGENT: Scleral Icterus is a systemic emergency. Seek immediate internal medicine evaluation."))
    if diagnosis == "Uveitis" and pain_level in ["Mild", "Severe"]:
        alerts.append(("urgent", "URGENT: Uveitis with pain is sight-threatening. Seek ophthalmologist immediately."))
    if halos == "Yes" and diagnosis == "Cataract":
        alerts.append(("info", "Symptom Match: Halos around lights strongly support a Cataract diagnosis."))
    if floaters == "Yes" and diagnosis not in ["Uveitis", "Normal"]:
        alerts.append(("warning", "Floaters Reported: Consider ruling out Vitreous Detachment or Retinal Tear with an eye specialist."))
    if light_sensitivity == "Yes" and diagnosis == "Uveitis":
        alerts.append(("urgent", "URGENT: Light sensitivity with Uveitis is sight-threatening — seek immediate care."))
    if discharge == "Thick/Yellow" and diagnosis == "Conjunctivitis":
        alerts.append(("info", "Symptom Match: Thick/yellow discharge supports Bacterial Conjunctivitis."))
    if duration == ">1 month" and diagnosis in ["Conjunctivitis", "Eyelid"]:
        alerts.append(("warning", "Chronic Duration: Symptoms lasting over a month warrant evaluation for Chlamydial infection or a persistent Chalazion."))
    return alerts


def analyze_symptoms(
    diagnosis: str,
    pain_level: str,
    vision_loss: str,
    itchiness: str,
    halos: str = "No",
    discharge: str = "None",
    light_sensitivity: str = "No",
    floaters: str = "No",
    duration: str = "Not Sure",
) -> List[str]:
    alerts = _build_symptom_alerts(
        diagnosis, pain_level, vision_loss, itchiness,
        halos=halos, discharge=discharge,
        light_sensitivity=light_sensitivity, floaters=floaters, duration=duration,
    )
    return [f"{_SEVERITY_ICON[sev]} {msg}" for sev, msg in alerts]


def analyze_symptoms_structured(
    diagnosis: str,
    pain_level: str,
    vision_loss: str,
    itchiness: str,
    halos: str = "No",
    discharge: str = "None",
    light_sensitivity: str = "No",
    floaters: str = "No",
    duration: str = "Not Sure",
) -> List[Dict[str, str]]:
    alerts = _build_symptom_alerts(
        diagnosis, pain_level, vision_loss, itchiness,
        halos=halos, discharge=discharge,
        light_sensitivity=light_sensitivity, floaters=floaters, duration=duration,
    )
    return [{"severity": sev, "message": msg} for sev, msg in alerts]

@app.get("/")
def read_root():
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    if gemini_key:
        chat_backend = f"Google Gemini ({GEMINI_MODEL})"
    elif ollama_url:
        chat_backend = f"Ollama ({os.getenv('OLLAMA_MODEL', 'llama3.2:3b')})"
    else:
        chat_backend = "Not Configured"
    return {
        "status": "OphthalmoAI System Ready",
        "device": str(DEVICE),
        "router_loaded": ROUTER_MODEL is not None,
        "specialists_loaded": len(SPECIALIST_MODELS),
        "chat_backend": chat_backend
    }

@app.get("/health")
def health_check():
    return {"ok": True, "device": str(DEVICE)}

@app.get("/ready")
def readiness_check(response: Response):
    ready = ROUTER_MODEL is not None
    if not ready:
        response.status_code = 503
    return {
        "ok": ready,
        "router_loaded": ready,
        "specialists_loaded": len(SPECIALIST_MODELS)
    }


@app.get("/conditions")
def get_conditions():
    conditions = []
    for key, info in MEDICAL_INFO.items():
        conditions.append({
            "key": key,
            "name": info.get("name", key),
            "group": info.get("group", "Unknown"),
            "color": info.get("color", "#64748B"),
            "description": info.get("description", ""),
            "symptoms": info.get("symptoms", []),
            "treatment": info.get("treatment", []),
            "precautions": info.get("precautions", []),
            "severity": info.get("severity", "Unknown"),
            "advice": info.get("advice", ""),
        })
    return {"conditions": conditions}


@app.post("/predict")
@_rate_limited(os.getenv("PREDICT_RATE_LIMIT", "10/minute"))
async def predict(
    request: Request,
    file: UploadFile = File(...),
    pain: str = Form(...),
    vision: str = Form(...),
    itch: str = Form(...),
    halos: str = Form(default="No"),
    discharge: str = Form(default="None"),
    light_sens: str = Form(default="No"),
    floaters: str = Form(default="No"),
    duration: str = Form(default="Not Sure"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
):
    client_ip = request.client.host if request.client else None
    user_id = current_user.id if current_user else None

    if ROUTER_MODEL is None:
        raise HTTPException(
            status_code=503,
            detail="AI diagnostic system offline. Train and load models first (see README).",
        )

    if file.content_type and file.content_type not in ALLOWED_CONTENT_TYPES:
        log_event(db, "predict", success=False, user_id=user_id, ip_address=client_ip,
                   error_detail=f"unsupported content type: {file.content_type}")
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported file type: {file.content_type}. Allowed types: "
                    f"{', '.join(sorted(ALLOWED_CONTENT_TYPES))}",
        )

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        log_event(db, "predict", success=False, user_id=user_id, ip_address=client_ip,
                   error_detail="file too large")
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds the {MAX_FILE_SIZE // (1024 * 1024)} MB upload limit.",
        )

    try:
        image = Image.open(io.BytesIO(contents)).convert('RGB')
    except Exception:
        log_event(db, "predict", success=False, user_id=user_id, ip_address=client_ip,
                   error_detail="invalid image")
        raise HTTPException(status_code=422, detail="File is not a valid image.")

    iqa_acceptable, iqa_warnings = (True, [])
    if ENABLE_IQA:
        try:
            iqa_acceptable, iqa_warnings = assess_image_quality(image)
        except Exception as iqa_err:
            logger.warning("predict.iqa_failed", error=str(iqa_err))

    try:
        input_tensor = preprocess(image).to(DEVICE).unsqueeze(0)
        with torch.no_grad():
            router_out = ROUTER_MODEL(input_tensor)
            router_probs = torch.nn.functional.softmax(router_out[0], dim=0)
            group_idx = torch.argmax(router_probs).item()
            group_conf = router_probs[group_idx].item()
        spec_data = SPECIALIST_MODELS.get(group_idx)
        if not spec_data:
            raise HTTPException(
                status_code=503,
                detail=f"Specialist model for group {group_idx} not loaded.",
            )
        group_key = GROUP_KEY_BY_IDX.get(group_idx, "unknown")
        calibration_temperature = CALIBRATION_REGISTRY.get(group_key)
        is_calibrated = CALIBRATION_REGISTRY.is_calibrated(group_key)

        heatmap_base64 = None
        uncertainty_value: Optional[float] = None

        if spec_data['type'] == 'direct':
            diagnosis = spec_data['class']
            confidence = group_conf * 100
            probs_dict = {diagnosis: 1.0}
        else:
            model_for_cam = spec_data['model']
            with torch.no_grad():
                out = model_for_cam(input_tensor)
                calibrated_out = apply_temperature(out[0], calibration_temperature)
                probs = torch.nn.functional.softmax(calibrated_out, dim=0)
                class_idx = torch.argmax(probs).item()
            diagnosis = spec_data['classes'][class_idx]
            confidence = probs[class_idx].item() * 100
            probs_dict = {
                spec_data['classes'][i]: float(probs[i].item())
                for i in range(len(spec_data['classes']))
            }

            if ENABLE_UNCERTAINTY:
                try:
                    _, uncertainty_value = mc_dropout_predict(
                        model_for_cam, input_tensor, n_passes=MC_DROPOUT_PASSES
                    )
                except Exception as unc_err:
                    logger.warning("predict.uncertainty_failed", error=str(unc_err))
                    uncertainty_value = None

            try:
                target_layer = [model_for_cam.features[-1]]
                cam = GradCAM(model=model_for_cam, target_layers=target_layer)
                grayscale = cam(
                    input_tensor=input_tensor,
                    targets=[ClassifierOutputTarget(class_idx)]
                )
                rgb_img = np.float32(image.resize((380, 380))) / 255
                vis = show_cam_on_image(rgb_img, grayscale[0, :], use_rgb=True)
                buff = io.BytesIO()
                Image.fromarray(vis).save(buff, format="JPEG", quality=85)
                heatmap_base64 = base64.b64encode(buff.getvalue()).decode("utf-8")
            except Exception as cam_err:
                print(f"Grad-CAM warning: {cam_err}")

        hybrid_warnings = analyze_symptoms(
            diagnosis, pain, vision, itch,
            halos=halos, discharge=discharge,
            light_sensitivity=light_sens, floaters=floaters, duration=duration,
        )
        hybrid_warnings_structured = analyze_symptoms_structured(
            diagnosis, pain, vision, itch,
            halos=halos, discharge=discharge,
            light_sensitivity=light_sens, floaters=floaters, duration=duration,
        )

        review_payload = build_review_payload(
            diagnosis,
            confidence / 100.0,
            uncertainty_value if uncertainty_value is not None else 0.0,
        )

        code_entry = get_clinical_code(diagnosis)

        details = MEDICAL_INFO.get(diagnosis, {}).copy()
        if not details:
            details = {
                "description": "No detailed information available.",
                "severity": "Unknown",
                "advice": "Please consult an ophthalmologist.",
                "treatment": [],
                "symptoms": [],
                "precautions": [],
                "analysis": ""
            }

        response_body = {
            "group_name": spec_data.get('group_name', 'Unknown'),
            "diagnosis": diagnosis,
            "confidence": round(confidence, 2),
            "heatmap": f"data:image/jpeg;base64,{heatmap_base64}" if heatmap_base64 else None,
            "details": details,
            "hybrid_warnings": hybrid_warnings,
            "hybrid_warnings_structured": hybrid_warnings_structured,
            "probabilities": probs_dict,
            "calibrated": is_calibrated,
            "calibration_temperature": round(calibration_temperature, 4),
            "uncertainty": review_payload["uncertainty"],
            "requires_human_review": review_payload["requires_human_review"],
            "review_reasons": review_payload["review_reasons"],
            "icd10_code": code_entry["icd10"],
            "snomed_code": code_entry["snomed_ct"],
            "urgency": code_entry["urgency"],
            "urgency_rank": code_entry["urgency_rank"],
            "referral": code_entry["referral"],
            "escalation_message": code_entry["escalation_message"],
            "iqa_acceptable": iqa_acceptable,
            "iqa_warnings": iqa_warnings,
        }

        scan_id = None
        if PERSIST_SCANS:
            try:
                scan = ScanResult(
                    user_id=user_id,
                    diagnosis=diagnosis,
                    confidence=round(confidence, 2),
                    group_name=spec_data.get('group_name', 'Unknown'),
                    probabilities=probs_dict,
                    calibrated=is_calibrated,
                    calibration_temperature=calibration_temperature,
                    uncertainty=review_payload["uncertainty"],
                    requires_human_review=review_payload["requires_human_review"],
                    review_reasons=review_payload["review_reasons"],
                    icd10_code=code_entry["icd10"],
                    snomed_code=code_entry["snomed_ct"],
                    urgency=code_entry["urgency"],
                    urgency_rank=code_entry["urgency_rank"],
                    hybrid_warnings=hybrid_warnings,
                    hybrid_warnings_structured=hybrid_warnings_structured,
                    iqa_acceptable=iqa_acceptable,
                    iqa_warnings=iqa_warnings,
                    symptoms_reported={
                        "pain": pain, "vision": vision, "itch": itch,
                        "halos": halos, "discharge": discharge,
                        "light_sensitivity": light_sens, "floaters": floaters,
                        "duration": duration,
                    },
                    router_group_idx=group_idx,
                )
                db.add(scan)
                db.commit()
                db.refresh(scan)
                scan_id = scan.id
                response_body["scan_id"] = scan_id
            except Exception as persist_err:
                logger.error("predict.persist_failed", error=str(persist_err))
                db.rollback()

        log_event(
            db, "predict", success=True, user_id=user_id,
            resource_id=scan_id, resource_type="scan_result", ip_address=client_ip,
            metadata={
                "diagnosis": diagnosis,
                "confidence": round(confidence, 2),
                "urgency": code_entry["urgency"],
                "requires_human_review": review_payload["requires_human_review"],
            },
        )

        return response_body
    except HTTPException:
        raise
    except Exception as e:
        print(f"Prediction Error: {e}")
        import traceback
        traceback.print_exc()
        log_event(db, "predict", success=False, user_id=user_id, ip_address=client_ip,
                   error_detail=str(e))
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()


@app.post("/auth/register", response_model=TokenResponse, status_code=201)
async def register(payload: RegisterRequest, request: Request, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(status_code=422, detail="A valid email address is required.")
    if len(payload.password) < 8:
        raise HTTPException(status_code=422, detail="Password must be at least 8 characters.")

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    role = "patient"

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id, role=user.role)
    log_event(db, "register", success=True, user_id=user.id,
              ip_address=request.client.host if request.client else None)
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@app.post("/auth/token", response_model=TokenResponse)
async def login(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    client_ip = request.client.host if request.client else None
    user = authenticate_user(db, email, password)
    if not user:
        log_event(db, "login", success=False, ip_address=client_ip,
                   error_detail=f"failed login attempt for {email.strip().lower()}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject=user.id, role=user.role)
    log_event(db, "login", success=True, user_id=user.id, ip_address=client_ip)
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@app.get("/auth/me")
async def get_me(current_user: User = Depends(require_role("patient", "clinician", "admin"))):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "created_at": current_user.created_at,
    }


@app.get("/scans/history")
async def scan_history(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient", "clinician", "admin")),
    limit: int = 50,
):
    query = db.query(ScanResult).order_by(ScanResult.created_at.desc())
    if current_user.role == "patient":
        query = query.filter(ScanResult.user_id == current_user.id)
    scans = query.limit(min(limit, 200)).all()
    return {
        "scans": [
            {
                "id": s.id,
                "diagnosis": s.diagnosis,
                "confidence": s.confidence,
                "urgency": s.urgency,
                "requires_human_review": s.requires_human_review,
                "icd10_code": s.icd10_code,
                "has_override": s.override is not None,
                "created_at": s.created_at,
            }
            for s in scans
        ]
    }


@app.get("/scans/{scan_id}")
async def get_scan(
    scan_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("patient", "clinician", "admin")),
):
    scan = db.query(ScanResult).filter(ScanResult.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")
    if current_user.role == "patient" and scan.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="You do not have access to this scan.")

    log_event(db, "view_scan", user_id=current_user.id, resource_id=scan_id,
               resource_type="scan_result")

    override = scan.override
    return {
        "id": scan.id,
        "diagnosis": scan.diagnosis,
        "confidence": scan.confidence,
        "group_name": scan.group_name,
        "probabilities": scan.probabilities,
        "calibrated": scan.calibrated,
        "uncertainty": scan.uncertainty,
        "requires_human_review": scan.requires_human_review,
        "review_reasons": scan.review_reasons,
        "icd10_code": scan.icd10_code,
        "snomed_code": scan.snomed_code,
        "urgency": scan.urgency,
        "hybrid_warnings_structured": scan.hybrid_warnings_structured,
        "iqa_acceptable": scan.iqa_acceptable,
        "iqa_warnings": scan.iqa_warnings,
        "symptoms_reported": scan.symptoms_reported,
        "created_at": scan.created_at,
        "override": {
            "verdict": override.verdict,
            "corrected_diagnosis": override.corrected_diagnosis,
            "corrected_icd10": override.corrected_icd10,
            "notes": override.notes,
            "clinician_id": override.clinician_id,
            "created_at": override.created_at,
        } if override else None,
    }


@app.post("/scans/{scan_id}/override", status_code=201)
async def override_scan(
    scan_id: str,
    payload: OverrideRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("clinician", "admin")),
):
    valid_verdicts = {"agree", "disagree", "inconclusive", "insufficient_image_quality"}
    if payload.verdict not in valid_verdicts:
        raise HTTPException(
            status_code=422,
            detail=f"verdict must be one of {sorted(valid_verdicts)}.",
        )
    if payload.verdict == "disagree" and not payload.corrected_diagnosis:
        raise HTTPException(
            status_code=422,
            detail="corrected_diagnosis is required when verdict is 'disagree'.",
        )

    scan = db.query(ScanResult).filter(ScanResult.id == scan_id).first()
    if not scan:
        raise HTTPException(status_code=404, detail="Scan not found.")

    existing = db.query(ClinicianOverride).filter(ClinicianOverride.scan_id == scan_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="This scan already has a clinician override recorded.")

    override = ClinicianOverride(
        scan_id=scan_id,
        clinician_id=current_user.id,
        verdict=payload.verdict,
        corrected_diagnosis=payload.corrected_diagnosis,
        corrected_icd10=payload.corrected_icd10,
        notes=payload.notes,
    )
    db.add(override)
    db.commit()
    db.refresh(override)

    log_event(
        db, "clinician_override", user_id=current_user.id, resource_id=scan_id,
        resource_type="scan_result",
        metadata={"verdict": payload.verdict, "corrected_diagnosis": payload.corrected_diagnosis},
    )
    return {"id": override.id, "scan_id": scan_id, "verdict": override.verdict}


@app.get("/admin/audit-logs")
async def list_audit_logs(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    limit: int = 100,
    action: Optional[str] = None,
):
    query = db.query(AuditLog).order_by(AuditLog.timestamp.desc())
    if action:
        query = query.filter(AuditLog.action == action)
    logs = query.limit(min(limit, 500)).all()
    return {
        "logs": [
            {
                "id": l.id,
                "action": l.action,
                "user_id": l.user_id,
                "resource_id": l.resource_id,
                "resource_type": l.resource_type,
                "success": l.success,
                "error_detail": l.error_detail,
                "ip_address": l.ip_address,
                "timestamp": l.timestamp,
            }
            for l in logs
        ]
    }


@app.get("/admin/model-registry")
async def get_model_registry(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
    group_key: Optional[str] = None,
):
    versions = model_registry.list_versions(db, group_key=group_key)
    return {
        "versions": [
            {
                "id": v.id,
                "group_key": v.group_key,
                "version_tag": v.version_tag,
                "architecture": v.architecture,
                "active": v.active,
                "val_accuracy": v.val_accuracy,
                "val_auc": v.val_auc,
                "calibration_temperature": v.calibration_temperature,
                "calibration_ece": v.calibration_ece,
                "registered_at": v.registered_at,
            }
            for v in versions
        ]
    }


@app.post("/admin/model-registry/activate")
async def activate_model_version(
    payload: ActivateModelRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role("admin")),
):
    try:
        version = model_registry.set_active(db, payload.version_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

    log_event(
        db, "admin_activate_model", user_id=current_user.id, resource_id=version.id,
        resource_type="model_version",
        metadata={"group_key": version.group_key, "version_tag": version.version_tag},
    )
    return {
        "id": version.id,
        "group_key": version.group_key,
        "version_tag": version.version_tag,
        "active": version.active,
        "note": "Registry updated. Restart the API process to load these weights for inference.",
    }


@app.post("/chat")
@_rate_limited(os.getenv("CHAT_RATE_LIMIT", "30/minute"))
async def chat_endpoint(request: Request, chat_request: ChatRequest):
    _chat_db = None
    try:
        from db import SessionLocal
        _chat_db = SessionLocal()
    except Exception:
        _chat_db = None

    system = OPHTHALMOLOGY_SYSTEM_PROMPT
    if chat_request.diagnosis_context:
        ctx = chat_request.diagnosis_context
        details = ctx.get('details', {})
        system += (
            f"\n\n--- CURRENT PATIENT AI SCREENING RESULT ---\n"
            f"Detected Condition: {ctx.get('diagnosis', 'Unknown')}\n"
            f"AI Confidence: {ctx.get('confidence', 0):.1f}%\n"
            f"Anatomical Group: {ctx.get('group_name', 'Unknown')}\n"
            f"Severity: {details.get('severity', 'Unknown')}\n"
            f"Clinical Advice: {details.get('advice', 'N/A')}\n"
            f"Note: This is an AI screening result only, not a clinical diagnosis."
        )
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip()
    reply = ""
    try:
        if gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)

            gemini_history = []
            for msg in chat_request.history:
                if msg.role == "user":
                    gemini_history.append({"role": "user", "parts": [msg.content]})
                elif msg.role == "assistant":
                    gemini_history.append({"role": "model", "parts": [msg.content]})

            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=system,
            )
            chat_session = model.start_chat(history=gemini_history)
            response = await chat_session.send_message_async(chat_request.message)
            reply = response.text
        elif ollama_url:
            import httpx
            model_supports_vision = any(
                kw in ollama_model.lower() for kw in VISION_MODEL_KEYWORDS
            )
            messages = [{"role": "system", "content": system}]
            for msg in chat_request.history:
                if msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})
            current_msg: Dict[str, Any] = {"role": "user", "content": chat_request.message}
            if model_supports_vision and chat_request.diagnosis_context:
                heatmap_data = chat_request.diagnosis_context.get('heatmap', '')
                if heatmap_data and "," in heatmap_data:
                    current_msg["images"] = [heatmap_data.split(",")[1]]
            messages.append(current_msg)
            payload = {
                "model": ollama_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_gpu": 0
                }
            }
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{ollama_url.rstrip('/')}/api/chat",
                    json=payload,
                    timeout=120.0
                )
                resp.raise_for_status()
                data = resp.json()
                reply = data.get("message", {}).get("content", "No response from local model.")
        else:
            reply = (
                "The AI Doctor chat is not configured yet.\n\n"
                "**Option 1 — Ollama (Free, Local, Recommended for RTX 3050):**\n"
                "1. Install Ollama from https://ollama.ai\n"
                "2. Run: `ollama pull llama3.2:3b`\n"
                "3. Set in .env: `OLLAMA_URL=http://localhost:11434`\n"
                "4. Set in .env: `OLLAMA_MODEL=llama3.2:3b`\n\n"
                "**Option 2 — Google Gemini (API key required):**\n"
                "1. Get a key from https://aistudio.google.com/app/apikey\n"
                "2. Set in .env: `GEMINI_API_KEY=your_key_here`"
            )
    except Exception as e:
        print(f"Chat Error: {e}")
        import traceback
        traceback.print_exc()
        reply = (
            "I encountered an error processing your message. "
            "Please check that Ollama is running (`ollama serve`) and the model is pulled. "
            "For urgent eye concerns, contact an ophthalmologist directly."
        )
    model_used = "gemini" if gemini_key else ("ollama" if ollama_url else "none")

    if _chat_db is not None:
        try:
            log_event(
                _chat_db, "chat", success=True,
                ip_address=request.client.host if request.client else None,
                metadata={"model_used": model_used,
                          "has_diagnosis_context": chat_request.diagnosis_context is not None},
            )
        except Exception:
            pass
        finally:
            _chat_db.close()

    return {"reply": reply, "model_used": model_used}

if __name__ == "__main__":
    os.environ.setdefault('OMP_NUM_THREADS', '4')
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False
    )
