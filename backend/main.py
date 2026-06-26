from __future__ import annotations

import gc
import io
import os
import sys
import warnings
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import numpy as np
import torch
import torch.nn as nn
import uvicorn
from fastapi import (
    Depends, FastAPI, File, Form, HTTPException,
    Request, Response, UploadFile, status,
)
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image
from pydantic import BaseModel
from sqlalchemy.orm import Session
from torchvision import models, transforms

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from pytorch_grad_cam import GradCAM
    from pytorch_grad_cam.utils.image import show_cam_on_image
    from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
    GRADCAM_AVAILABLE = True
except ImportError:
    GRADCAM_AVAILABLE = False

try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False

import base64

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from audit import log_event
from auth import (
    ROLE_HIERARCHY, JWT_SECRET_KEY,
    authenticate_user, create_access_token, decode_token,
    get_current_user, hash_password, require_role, revoke_token,
    oauth2_scheme,
)
from calibration import CalibrationRegistry, apply_temperature
from clinical_codes import get_clinical_code
from db import (
    AuditLog, ClinicianOverride, ModelVersion,
    ScanResult, User, create_tables, get_db,
)
from iqa import assess_image_quality
from logging_config import configure_logging, get_logger
from medical_data import MEDICAL_INFO
from model_registry import list_versions, set_active
from security import (
    RequestIDMiddleware,
    SecurityHeadersMiddleware,
    anonymise_ip,
    make_rate_limit_decorator,
    safe_error_detail,
    token_blacklist,
    validate_image_dimensions,
    validate_magic_bytes,
    ALLOWED_MIMES,
)
from storage import store as storage_store, presigned_url
from uncertainty import build_review_payload, mc_dropout_predict
from validators import (
    sanitise_chat_message,
    validate_email,
    validate_ollama_url_from_env,
    validate_password_strength,
)

configure_logging(json_output=os.getenv("LOG_FORMAT", "json").lower() == "json")
logger = get_logger("ophthalmoai")

_ENV = os.getenv("ENVIRONMENT", "development").strip().lower()
_IS_PROD = _ENV not in {"development", "dev", "test", "testing"}

MODELS_DIR    = os.getenv("MODELS_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "models"))
FORCE_CPU     = os.getenv("FORCE_CPU", "false").lower() in {"1", "true", "yes"}
DEVICE        = torch.device("cuda" if torch.cuda.is_available() and not FORCE_CPU else "cpu")
GEMINI_MODEL  = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()
MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE_BYTES", str(20 * 1024 * 1024)))

CALIBRATION_PATH    = os.path.join(MODELS_DIR, "calibration.json")
CALIBRATION_REGISTRY = CalibrationRegistry(CALIBRATION_PATH)
MC_DROPOUT_PASSES   = int(os.getenv("MC_DROPOUT_PASSES", "8"))
ENABLE_UNCERTAINTY  = os.getenv("ENABLE_UNCERTAINTY", "true").lower() in {"1", "true", "yes"}
ENABLE_IQA          = os.getenv("ENABLE_IQA", "true").lower() in {"1", "true", "yes"}
PERSIST_SCANS       = os.getenv("PERSIST_SCANS", "true").lower() in {"1", "true", "yes"}

GROUP_KEY_BY_IDX = {0: "eyelid", 1: "anterior", 2: "surface"}

HIERARCHY = {
    0: {"name": "Adnexal Oculoplastic",      "model_file": "specialist_eyelid.pth",    "classes": ["Eyelid"]},
    1: {"name": "Anterior Segment Pathology", "model_file": "specialist_anterior.pth",  "classes": ["Cataract", "Uveitis"]},
    2: {"name": "Ocular Surface Disorders",   "model_file": "specialist_surface.pth",   "classes": ["Conjunctivitis", "Jaundice", "Normal", "Pterygium"]},
}

ROUTER_MODEL: Optional[nn.Module] = None
SPECIALIST_MODELS: Dict[int, Any] = {}

OPHTHALMOLOGY_SYSTEM_PROMPT = """You are OphthalmoAI Doctor, a specialized AI assistant focused on
ophthalmology and eye health education. Provide accurate, empathetic responses about eye conditions
while always recommending professional consultation. Never diagnose definitively; always frame
results as 'AI screening'. For emergencies (sudden vision loss, chemical exposure, trauma), direct
to emergency care immediately."""

preprocess = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def build_router() -> nn.Module:
    model = models.mobilenet_v3_large(weights=None)
    model.classifier[3] = nn.Linear(model.classifier[3].in_features, len(HIERARCHY))
    return model


def build_specialist(num_classes: int) -> nn.Module:
    model = models.efficientnet_b4(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    return model


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ROUTER_MODEL, SPECIALIST_MODELS

    logger.info("startup.begin", device=str(DEVICE), environment=_ENV)

    if _IS_PROD and JWT_SECRET_KEY == "CHANGE_ME_BEFORE_PRODUCTION_DEPLOYMENT":
        raise RuntimeError(
            "JWT_SECRET_KEY is still the insecure default placeholder. "
            "Set a cryptographically random value before deploying to production. "
            "Generate one with:  python -c \"import secrets; print(secrets.token_hex(32))\""
        )

    try:
        validate_ollama_url_from_env()
    except RuntimeError as e:
        logger.error("startup.ollama_url_rejected", error=str(e))
        raise

    try:
        create_tables()
        logger.info("startup.db_ready")
    except Exception as exc:
        logger.error("startup.db_failed", error=str(exc))

    router = build_router()
    router_path = os.path.join(MODELS_DIR, "router.pth")
    if os.path.exists(router_path):
        try:
            router.load_state_dict(
                torch.load(router_path, map_location=DEVICE, weights_only=True),
                strict=False,
            )
            router.to(DEVICE).eval()
            ROUTER_MODEL = router
            logger.info("startup.router_loaded")
        except Exception as exc:
            logger.error("startup.router_load_failed", error=str(exc))
    else:
        logger.warning("startup.router_missing", path=router_path)

    for idx, info in HIERARCHY.items():
        classes = info["classes"]
        if len(classes) <= 1:
            SPECIALIST_MODELS[idx] = {
                "type": "direct", "class": classes[0], "group_name": info["name"]
            }
            continue
        model_path = os.path.join(MODELS_DIR, info["model_file"])
        model = build_specialist(len(classes))
        if os.path.exists(model_path):
            try:
                model.load_state_dict(
                    torch.load(model_path, map_location=DEVICE, weights_only=True)
                )
                model.to(DEVICE).eval()
                SPECIALIST_MODELS[idx] = {
                    "type": "model", "model": model,
                    "classes": classes, "group_name": info["name"],
                }
                logger.info("startup.specialist_loaded", group=info["name"])
            except Exception as exc:
                logger.error("startup.specialist_load_failed", group=info["name"], error=str(exc))
        else:
            logger.warning("startup.specialist_missing", path=model_path)

    yield

    logger.info("shutdown.begin")
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(
    lifespan=lifespan,
    title="OphthalmoAI API",
    version="2.1.0",
    docs_url=None if _IS_PROD else "/docs",
    redoc_url=None if _IS_PROD else "/redoc",
)

app.add_middleware(SecurityHeadersMiddleware, is_production=_IS_PROD)
app.add_middleware(RequestIDMiddleware)

_cors_origins_raw = os.getenv("CORS_ORIGINS", "*")
cors_origins = [o.strip() for o in _cors_origins_raw.split(",") if o.strip()]
_is_wildcard = cors_origins == ["*"]
_allow_credentials = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() in {"1", "true", "yes"}

if _is_wildcard and _allow_credentials:
    raise RuntimeError(
        "CORS_ORIGINS=* cannot be combined with CORS_ALLOW_CREDENTIALS=true. "
        "Set an explicit origin list in CORS_ORIGINS."
    )
if _is_wildcard and _IS_PROD:
    raise RuntimeError(
        "CORS_ORIGINS=* is not permitted in production. "
        "Set CORS_ORIGINS to a comma-separated list of allowed origins."
    )
if _is_wildcard:
    warnings.warn(
        "CORS_ORIGINS=* — acceptable for local development only. "
        "Always set explicit origins in production.",
        stacklevel=1,
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=_allow_credentials,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    expose_headers=["X-Request-ID"],
)

if SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

PREDICT_RATE_LIMIT = os.getenv("PREDICT_RATE_LIMIT", "10/minute")
CHAT_RATE_LIMIT    = os.getenv("CHAT_RATE_LIMIT",    "30/minute")
AUTH_RATE_LIMIT    = os.getenv("AUTH_RATE_LIMIT",    "20/minute")

_predict_limit = make_rate_limit_decorator(PREDICT_RATE_LIMIT)
_chat_limit    = make_rate_limit_decorator(CHAT_RATE_LIMIT)
_auth_limit    = make_rate_limit_decorator(AUTH_RATE_LIMIT)


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

def _build_symptom_alerts(diagnosis, pain_level, vision_loss, itchiness,
                           halos="No", discharge="None", light_sensitivity="No",
                           floaters="No", duration="Not Sure"):
    alerts = []
    if diagnosis == "Conjunctivitis" and pain_level == "Severe":
        alerts.append(("warning", "Pain Mismatch: Severe pain is unusual for Pink Eye. Rule out Glaucoma or Keratitis."))
    if vision_loss == "Yes" and diagnosis in ["Conjunctivitis", "Eyelid"]:
        alerts.append(("warning", "Vision Loss Warning: Surface/Eyelid conditions rarely affect vision."))
    if itchiness == "Yes" and diagnosis == "Conjunctivitis":
        alerts.append(("info", "Symptom Match: Itchiness strongly supports Allergic Conjunctivitis."))
    if diagnosis == "Jaundice":
        alerts.append(("urgent", "URGENT: Scleral Icterus is a systemic emergency. Seek immediate evaluation."))
    if diagnosis == "Uveitis" and pain_level in ["Mild", "Severe"]:
        alerts.append(("urgent", "URGENT: Uveitis with pain is sight-threatening. Seek ophthalmologist immediately."))
    if halos == "Yes" and diagnosis == "Cataract":
        alerts.append(("info", "Symptom Match: Halos around lights strongly support a Cataract diagnosis."))
    if floaters == "Yes" and diagnosis not in ["Uveitis", "Normal"]:
        alerts.append(("warning", "Floaters Reported: Consider ruling out Vitreous Detachment or Retinal Tear."))
    if light_sensitivity == "Yes" and diagnosis == "Uveitis":
        alerts.append(("urgent", "URGENT: Light sensitivity with Uveitis is sight-threatening."))
    if discharge == "Thick/Yellow" and diagnosis == "Conjunctivitis":
        alerts.append(("info", "Symptom Match: Thick/yellow discharge supports Bacterial Conjunctivitis."))
    if duration == ">1 month" and diagnosis in ["Conjunctivitis", "Eyelid"]:
        alerts.append(("warning", "Chronic Duration: Symptoms lasting over a month warrant further evaluation."))
    return alerts

def analyze_symptoms(diagnosis, pain_level, vision_loss, itchiness, **kwargs):
    alerts = _build_symptom_alerts(diagnosis, pain_level, vision_loss, itchiness, **kwargs)
    return [f"{_SEVERITY_ICON[s]} {m}" for s, m in alerts]

def analyze_symptoms_structured(diagnosis, pain_level, vision_loss, itchiness, **kwargs):
    alerts = _build_symptom_alerts(diagnosis, pain_level, vision_loss, itchiness, **kwargs)
    return [{"severity": s, "message": m} for s, m in alerts]


def _client_ip(request: Request) -> Optional[str]:
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


@app.get("/")
def read_root():
    gemini_key = os.getenv("GEMINI_API_KEY", "").strip()
    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    chat_backend = (
        f"Google Gemini ({GEMINI_MODEL})" if gemini_key
        else f"Ollama ({os.getenv('OLLAMA_MODEL', 'llama3.2:3b')})" if ollama_url
        else "Not Configured"
    )
    return {
        "status": "OphthalmoAI System Ready",
        "device": str(DEVICE),
        "router_loaded": ROUTER_MODEL is not None,
        "specialists_loaded": len(SPECIALIST_MODELS),
        "chat_backend": chat_backend,
        "version": "2.1.0",
    }

@app.get("/health")
def health_check():
    return {"ok": True, "device": str(DEVICE)}

@app.get("/ready")
def readiness_check(response: Response):
    ready = ROUTER_MODEL is not None
    if not ready:
        response.status_code = 503
    return {"ok": ready, "router_loaded": ready, "specialists_loaded": len(SPECIALIST_MODELS)}

@app.get("/conditions")
def get_conditions():
    return {"conditions": [
        {
            "key": k,
            "name": v.get("name", k),
            "group": v.get("group", ""),
            "color": v.get("color", "#64748B"),
            "description": v.get("description", ""),
            "symptoms": v.get("symptoms", []),
            "treatment": v.get("treatment", []),
            "precautions": v.get("precautions", []),
            "severity": v.get("severity", ""),
            "advice": v.get("advice", ""),
        }
        for k, v in MEDICAL_INFO.items()
    ]}


@app.post("/predict")
@_predict_limit
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
    client_ip = anonymise_ip(_client_ip(request))  
    user_id   = current_user.id if current_user else None
    req_id    = getattr(request.state, "request_id", None)

    if ROUTER_MODEL is None:
        raise HTTPException(503, detail="AI diagnostic system offline. Train and load models first.")

    if file.content_type and file.content_type.lower() not in ALLOWED_MIMES | {"application/octet-stream"}:
        log_event(db, "predict", success=False, user_id=user_id, ip_address=client_ip,
                  error_detail=f"rejected content-type: {file.content_type}")
        raise HTTPException(415, detail=f"Unsupported file type '{file.content_type}'.")

    contents = await file.read()

    if len(contents) > MAX_FILE_SIZE:
        log_event(db, "predict", success=False, user_id=user_id, ip_address=client_ip,
                  error_detail="file too large")
        raise HTTPException(413, detail=f"File exceeds the {MAX_FILE_SIZE // (1024*1024)} MB limit.")

    magic_ok, magic_result = validate_magic_bytes(contents, file.content_type)
    if not magic_ok:
        log_event(db, "predict", success=False, user_id=user_id, ip_address=client_ip,
                  error_detail=f"magic byte rejection: {magic_result}")
        raise HTTPException(415, detail=magic_result)

    dim_ok, dim_result = validate_image_dimensions(contents)
    if not dim_ok:
        raise HTTPException(422, detail=dim_result)

    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(422, detail="File could not be decoded as an image.")

    iqa_acceptable, iqa_warnings = (True, [])
    if ENABLE_IQA:
        try:
            iqa_acceptable, iqa_warnings = assess_image_quality(image)
        except Exception as iqa_err:
            logger.warning("predict.iqa_failed", error=str(iqa_err))

    try:
        input_tensor = preprocess(image).to(DEVICE).unsqueeze(0)

        with torch.no_grad():
            router_out   = ROUTER_MODEL(input_tensor)
            router_probs = torch.nn.functional.softmax(router_out[0], dim=0)
            group_idx    = int(torch.argmax(router_probs).item())
            group_conf   = float(router_probs[group_idx].item())

        spec_data = SPECIALIST_MODELS.get(group_idx)
        if not spec_data:
            raise HTTPException(503, detail=f"Specialist model for group {group_idx} not loaded.")

        group_key             = GROUP_KEY_BY_IDX.get(group_idx, "unknown")
        calibration_temperature = CALIBRATION_REGISTRY.get(group_key)
        is_calibrated         = CALIBRATION_REGISTRY.is_calibrated(group_key)
        heatmap_base64        = None
        uncertainty_value: Optional[float] = None

        if spec_data["type"] == "direct":
            diagnosis   = spec_data["class"]
            confidence  = group_conf * 100
            probs_dict  = {diagnosis: 1.0}
        else:
            model_for_cam = spec_data["model"]
            with torch.no_grad():
                out            = model_for_cam(input_tensor)
                calibrated_out = apply_temperature(out[0], calibration_temperature)
                probs          = torch.nn.functional.softmax(calibrated_out, dim=0)
                class_idx      = int(torch.argmax(probs).item())

            diagnosis  = spec_data["classes"][class_idx]
            confidence = float(probs[class_idx].item()) * 100
            probs_dict = {spec_data["classes"][i]: float(probs[i].item())
                          for i in range(len(spec_data["classes"]))}

            if ENABLE_UNCERTAINTY:
                try:
                    _, uncertainty_value = mc_dropout_predict(
                        model_for_cam, input_tensor, n_passes=MC_DROPOUT_PASSES
                    )
                except Exception as unc_err:
                    logger.warning("predict.uncertainty_failed", error=str(unc_err))

            if GRADCAM_AVAILABLE:
                try:
                    cam        = GradCAM(model=model_for_cam, target_layers=[model_for_cam.features[-1]])
                    grayscale  = cam(input_tensor=input_tensor, targets=[ClassifierOutputTarget(class_idx)])
                    rgb_img    = np.float32(image.resize((380, 380))) / 255
                    vis        = show_cam_on_image(rgb_img, grayscale[0, :], use_rgb=True)
                    buff       = io.BytesIO()
                    Image.fromarray(vis).save(buff, format="JPEG", quality=85)
                    heatmap_base64 = base64.b64encode(buff.getvalue()).decode("utf-8")
                except Exception as cam_err:
                    logger.warning("predict.gradcam_failed", error=str(cam_err))

        hybrid_warnings            = analyze_symptoms(
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
        details    = MEDICAL_INFO.get(diagnosis, {
            "description": "No detailed information available.",
            "severity": "Unknown",
            "advice": "Please consult an ophthalmologist.",
            "treatment": [], "symptoms": [], "precautions": [], "analysis": "",
        })

        response_body: Dict[str, Any] = {
            "group_name":               spec_data.get("group_name", "Unknown"),
            "diagnosis":                diagnosis,
            "confidence":               round(confidence, 2),
            "heatmap":                  f"data:image/jpeg;base64,{heatmap_base64}" if heatmap_base64 else None,
            "details":                  details,
            "hybrid_warnings":          hybrid_warnings,
            "hybrid_warnings_structured": hybrid_warnings_structured,
            "probabilities":            probs_dict,
            "calibrated":               is_calibrated,
            "calibration_temperature":  round(calibration_temperature, 4),
            "uncertainty":              review_payload["uncertainty"],
            "requires_human_review":    review_payload["requires_human_review"],
            "review_reasons":           review_payload["review_reasons"],
            "icd10_code":               code_entry["icd10"],
            "snomed_code":              code_entry["snomed_ct"],
            "urgency":                  code_entry["urgency"],
            "urgency_rank":             code_entry["urgency_rank"],
            "referral":                 code_entry["referral"],
            "escalation_message":       code_entry["escalation_message"],
            "iqa_acceptable":           iqa_acceptable,
            "iqa_warnings":             iqa_warnings,
        }

        scan_id = None
        if PERSIST_SCANS:
            try:
                scan = ScanResult(
                    user_id=user_id, diagnosis=diagnosis,
                    confidence=round(confidence, 2),
                    group_name=spec_data.get("group_name", "Unknown"),
                    probabilities=probs_dict, calibrated=is_calibrated,
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
                    iqa_acceptable=iqa_acceptable, iqa_warnings=iqa_warnings,
                    symptoms_reported={
                        "pain": pain, "vision": vision, "itch": itch,
                        "halos": halos, "discharge": discharge,
                        "light_sensitivity": light_sens,
                        "floaters": floaters, "duration": duration,
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

        log_event(db, "predict", success=True, user_id=user_id,
                  resource_id=scan_id, resource_type="scan_result", ip_address=client_ip,
                  metadata={"diagnosis": diagnosis, "confidence": round(confidence, 2),
                            "urgency": code_entry["urgency"],
                            "requires_human_review": review_payload["requires_human_review"]})
        return response_body

    except HTTPException:
        raise
    except Exception as exc:
        log_event(db, "predict", success=False, user_id=user_id,
                  ip_address=client_ip, error_detail=str(exc))
        raise HTTPException(500, detail=safe_error_detail(exc, request_id=req_id))
    finally:
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()


@app.post("/auth/register", response_model=TokenResponse, status_code=201)
@_auth_limit
async def register(
    request: Request,
    payload: RegisterRequest,
    db: Session = Depends(get_db),
):
    email_ok, email_or_err = validate_email(payload.email)
    if not email_ok:
        raise HTTPException(422, detail=email_or_err)

    pw_ok, pw_err = validate_password_strength(payload.password)
    if not pw_ok:
        raise HTTPException(422, detail=pw_err)

    email = email_or_err  # normalised
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(409, detail="An account with this email already exists.")

    user = User(
        email=email,
        hashed_password=hash_password(payload.password),
        full_name=payload.full_name,
        role="patient",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(subject=user.id, role=user.role)
    log_event(db, "register", success=True, user_id=user.id,
              ip_address=anonymise_ip(_client_ip(request)))
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@app.post("/auth/token", response_model=TokenResponse)
@_auth_limit
async def login(
    request: Request,
    db: Session = Depends(get_db),
    email: str = Form(...),
    password: str = Form(...),
):
    client_ip = anonymise_ip(_client_ip(request))

    user, error = authenticate_user(db, email, password)
    if error or not user:
        log_event(db, "login", success=False, ip_address=client_ip,
                  error_detail=error or "unknown")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=error or "Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user.last_login_at = datetime.now(timezone.utc)
    db.commit()

    token = create_access_token(subject=user.id, role=user.role)
    log_event(db, "login", success=True, user_id=user.id, ip_address=client_ip)
    return TokenResponse(access_token=token, role=user.role, user_id=user.id)


@app.post("/auth/logout", status_code=204)
async def logout(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
):
    if token:
        revoke_token(token)
    return Response(status_code=204)


@app.get("/auth/me")
async def get_me(current_user: User = Depends(require_role("patient", "clinician", "admin"))):
    return {
        "id": current_user.id,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role,
        "created_at": current_user.created_at,
    }


@app.post("/chat")
@_chat_limit
async def chat_endpoint(
    request: Request,
    chat_request: ChatRequest,
    db: Session = Depends(get_db),              
    current_user: Optional[User] = Depends(get_current_user),
):
    req_id    = getattr(request.state, "request_id", None)
    client_ip = anonymise_ip(_client_ip(request))

    safe_ok, safe_msg = sanitise_chat_message(chat_request.message)
    if not safe_ok:
        raise HTTPException(422, detail=safe_msg)

    system = OPHTHALMOLOGY_SYSTEM_PROMPT
    if chat_request.diagnosis_context:
        ctx     = chat_request.diagnosis_context
        details = ctx.get("details", {})
        system += (
            f"\n\n--- CURRENT PATIENT AI SCREENING RESULT ---\n"
            f"Detected Condition: {ctx.get('diagnosis', 'Unknown')}\n"
            f"AI Confidence: {ctx.get('confidence', 0):.1f}%\n"
            f"Anatomical Group: {ctx.get('group_name', 'Unknown')}\n"
            f"Severity: {details.get('severity', 'Unknown')}\n"
            f"Clinical Advice: {details.get('advice', 'N/A')}\n"
            f"Note: This is an AI screening result only, not a clinical diagnosis."
        )

    gemini_key  = os.getenv("GEMINI_API_KEY", "").strip()
    ollama_url  = os.getenv("OLLAMA_URL", "").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip()
    reply        = ""
    model_used   = "none"

    try:
        if gemini_key:
            import google.generativeai as genai
            genai.configure(api_key=gemini_key)
            gemini_history = [
                {"role": "user" if m.role == "user" else "model", "parts": [m.content]}
                for m in chat_request.history
                if m.role in ("user", "assistant")
            ]
            model = genai.GenerativeModel(
                model_name=GEMINI_MODEL,
                system_instruction=system,
            )
            chat_session = model.start_chat(history=gemini_history)
            response = await chat_session.send_message_async(safe_msg)
            reply      = response.text
            model_used = "gemini"

        elif ollama_url:
            import httpx
            messages = [{"role": "system", "content": system}]
            for m in chat_request.history:
                if m.role in ("user", "assistant"):
                    messages.append({"role": m.role, "content": m.content})
            messages.append({"role": "user", "content": safe_msg})

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{ollama_url.rstrip('/')}/api/chat",
                    json={"model": ollama_model, "messages": messages, "stream": False},
                    timeout=120.0,
                )
                resp.raise_for_status()
                reply      = resp.json().get("message", {}).get("content", "No response from local model.")
                model_used = "ollama"

        else:
            reply = (
                "The AI Doctor chat is not configured. "
                "Set GEMINI_API_KEY or OLLAMA_URL in your .env file."
            )

    except Exception as exc:
        logger.error("chat.error", error=str(exc), request_id=req_id)
        reply = (
            "I encountered an error processing your message. "
            "Please try again. For urgent eye concerns, contact a qualified ophthalmologist."
        )

    log_event(
        db, "chat", success=True,
        user_id=current_user.id if current_user else None,
        ip_address=client_ip,
        metadata={"model_used": model_used,
                  "has_diagnosis_context": chat_request.diagnosis_context is not None},
    )
    return {"reply": reply, "model_used": model_used}


if __name__ == "__main__":
    os.environ.setdefault("OMP_NUM_THREADS", "4")
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=False,
        access_log=not _IS_PROD,  
    )
