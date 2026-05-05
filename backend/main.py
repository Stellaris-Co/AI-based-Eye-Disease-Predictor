from fastapi import FastAPI, File, UploadFile, Form
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
from contextlib import asynccontextmanager
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image

# Load environment variables if python-dotenv is available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# --- IMPORT MEDICAL DATA ---
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from medical_data import MEDICAL_INFO

# --- CONFIGURATION ---
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
MODELS_DIR = os.path.join(project_root, "models")
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# --- HIERARCHY SETUP ---
HIERARCHY = {
    0: {'name': 'Adnexal Oculoplastic', 'model_file': 'specialist_eyelid.pth', 'classes': ['Eyelid']},
    1: {'name': 'Anterior Segment Pathology', 'model_file': 'specialist_anterior.pth', 'classes': ['Cataract', 'Uveitis']},
    2: {'name': 'Ocular Surface Disorders', 'model_file': 'specialist_surface.pth', 'classes': ['Conjunctivitis', 'Jaundice', 'Normal', 'Pterygium']}
}

# --- GLOBAL MODEL STORAGE ---
ROUTER_MODEL = None
SPECIALIST_MODELS = {}

# --- VISION-CAPABLE OLLAMA MODELS (support image input) ---
VISION_MODEL_KEYWORDS = ['llava', 'moondream', 'bakllava', 'vision', 'llava-phi3', 'minicpm-v']

# --- AI DOCTOR SYSTEM PROMPT ---
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


# --- MODEL ARCHITECTURE ---
def build_router():
    model = models.mobilenet_v3_large(weights=None)
    model.classifier[3] = torch.nn.Linear(model.classifier[3].in_features, len(HIERARCHY))
    return model

def build_specialist(num_classes):
    model = models.efficientnet_b4(weights=None)
    model.classifier[1] = torch.nn.Linear(model.classifier[1].in_features, num_classes)
    return model

# --- PREPROCESSING ---
preprocess = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])


@asynccontextmanager
async def lifespan(app: FastAPI):
    global ROUTER_MODEL, SPECIALIST_MODELS
    print(f"🚀 Loading AI System onto {DEVICE}...")

    # 1. Load Router
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

    # 2. Load Specialists
    for idx, info in HIERARCHY.items():
        classes = info['classes']
        model_path = os.path.join(MODELS_DIR, info['model_file'])

        # Single-class groups use direct pass-through (no separate model needed)
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

    print("👋 Shutting down AI System.")
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()


app = FastAPI(lifespan=lifespan, title="OphthalmoAI API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─────────────────────────────────────────────────────────────────
#  PYDANTIC MODELS FOR CHAT
# ─────────────────────────────────────────────────────────────────
class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    diagnosis_context: Optional[Dict[str, Any]] = None


# ─────────────────────────────────────────────────────────────────
#  HELPER: SYMPTOM ANALYSIS
# ─────────────────────────────────────────────────────────────────
def analyze_symptoms(diagnosis: str, pain_level: str, vision_loss: str, itchiness: str) -> List[str]:
    alerts = []  # renamed from 'warnings' to avoid shadowing stdlib name
    if diagnosis == "Conjunctivitis" and pain_level == "Severe":
        alerts.append("⚠️ Pain Mismatch: Severe pain is unusual for Pink Eye. Rule out Glaucoma or Keratitis.")
    if vision_loss == "Yes" and diagnosis in ["Conjunctivitis", "Eyelid"]:
        alerts.append("⚠️ Vision Loss Warning: Surface/Eyelid conditions rarely affect vision. Consider Keratitis or Uveitis.")
    if itchiness == "Yes" and diagnosis == "Conjunctivitis":
        alerts.append("✅ Symptom Match: Itchiness strongly supports Allergic Conjunctivitis.")
    if diagnosis == "Jaundice":
        alerts.append("🚨 URGENT: Scleral Icterus is a systemic emergency. Seek immediate internal medicine evaluation.")
    if diagnosis == "Uveitis" and pain_level in ["Mild", "Severe"]:
        alerts.append("🚨 URGENT: Uveitis with pain is sight-threatening. Seek ophthalmologist immediately.")
    return alerts


# ─────────────────────────────────────────────────────────────────
#  ENDPOINTS
# ─────────────────────────────────────────────────────────────────
@app.get("/")
def read_root():
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    if anthropic_key:
        chat_backend = "Anthropic Claude"
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


@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    pain: str = Form(...),
    vision: str = Form(...),
    itch: str = Form(...)
):
    if ROUTER_MODEL is None:
        return {"error": "AI diagnostic system offline. Train and load models first (see README)."}

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        input_tensor = preprocess(image).to(DEVICE).unsqueeze(0)

        # STAGE 1: ROUTER — determines anatomical group
        with torch.no_grad():
            router_out = ROUTER_MODEL(input_tensor)
            router_probs = torch.nn.functional.softmax(router_out[0], dim=0)
            group_idx = torch.argmax(router_probs).item()
            group_conf = router_probs[group_idx].item()

        spec_data = SPECIALIST_MODELS.get(group_idx)
        if not spec_data:
            return {"error": f"Specialist model for group {group_idx} not loaded."}

        heatmap_base64 = None

        # STAGE 2: SPECIALIST DIAGNOSIS
        if spec_data['type'] == 'direct':
            # Single-class group — no sub-model needed
            diagnosis = spec_data['class']
            confidence = group_conf * 100
            probs_dict = {diagnosis: 1.0}

        else:
            model_for_cam = spec_data['model']
            with torch.no_grad():
                out = model_for_cam(input_tensor)
                probs = torch.nn.functional.softmax(out[0], dim=0)
                class_idx = torch.argmax(probs).item()

            diagnosis = spec_data['classes'][class_idx]
            confidence = probs[class_idx].item() * 100
            # Return as 0-1 floats; frontend multiplies by 100 for display
            probs_dict = {
                spec_data['classes'][i]: float(probs[i].item())
                for i in range(len(spec_data['classes']))
            }

            # Generate Grad-CAM Heatmap
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

        # STAGE 3: HYBRID SYMPTOM CROSS-CHECK
        hybrid_warnings = analyze_symptoms(diagnosis, pain, vision, itch)
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

        return {
            "group_name": spec_data.get('group_name', 'Unknown'),
            "diagnosis": diagnosis,
            "confidence": round(confidence, 2),
            "heatmap": f"data:image/jpeg;base64,{heatmap_base64}" if heatmap_base64 else None,
            "details": details,
            "hybrid_warnings": hybrid_warnings,
            "probabilities": probs_dict
        }

    except Exception as e:
        print(f"Prediction Error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": f"Analysis failed: {str(e)}"}

    finally:
        # Free GPU memory so Ollama LLM has headroom
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            gc.collect()


@app.post("/chat")
async def chat_endpoint(request: ChatRequest):
    """AI Doctor chat via Anthropic Claude API or local Ollama (llama3.2:3b recommended)."""

    # Build system prompt, inject diagnosis context if available
    system = OPHTHALMOLOGY_SYSTEM_PROMPT
    if request.diagnosis_context:
        ctx = request.diagnosis_context
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

    # Read config — OLLAMA_URL defaults to empty (not configured) unless explicitly set
    anthropic_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    ollama_url = os.getenv("OLLAMA_URL", "").strip()
    ollama_model = os.getenv("OLLAMA_MODEL", "llama3.2:3b").strip()

    reply = ""

    try:
        if anthropic_key:
            # ── Anthropic Claude ──────────────────────────────────────────────
            messages = []
            for msg in request.history:
                if msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})
            messages.append({"role": "user", "content": request.message})

            import anthropic
            client = anthropic.AsyncAnthropic(api_key=anthropic_key)
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system=system,
                messages=messages
            )
            reply = response.content[0].text

        elif ollama_url:
            # ── Ollama Local LLM ──────────────────────────────────────────────
            # Recommended: llama3.2:3b (~2GB VRAM, fits RTX 3050 6GB comfortably)
            # For vision support use llava variants; llama3.2 is text-only.
            import httpx

            # Only pass heatmap image if the model actually supports vision
            model_supports_vision = any(
                kw in ollama_model.lower() for kw in VISION_MODEL_KEYWORDS
            )

            messages = [{"role": "system", "content": system}]
            for msg in request.history:
                if msg.role in ("user", "assistant"):
                    messages.append({"role": msg.role, "content": msg.content})

            current_msg: Dict[str, Any] = {"role": "user", "content": request.message}

            # Attach heatmap image only for vision-capable models
            if model_supports_vision and request.diagnosis_context:
                heatmap_data = request.diagnosis_context.get('heatmap', '')
                if heatmap_data and "," in heatmap_data:
                    current_msg["images"] = [heatmap_data.split(",")[1]]

            messages.append(current_msg)

            payload = {
                "model": ollama_model,
                "messages": messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "num_gpu": 0  # <--- This forces Ollama to use CPU only
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
            # ── No LLM Configured ─────────────────────────────────────────────
            reply = (
                "The AI Doctor chat is not configured yet.\n\n"
                "**Option 1 — Ollama (Free, Local, Recommended for RTX 3050):**\n"
                "1. Install Ollama from https://ollama.ai\n"
                "2. Run: `ollama pull llama3.2:3b`\n"
                "3. Set in .env: `OLLAMA_URL=http://localhost:11434`\n"
                "4. Set in .env: `OLLAMA_MODEL=llama3.2:3b`\n\n"
                "**Option 2 — Anthropic Claude (API key required):**\n"
                "1. Get a key from https://console.anthropic.com\n"
                "2. Set in .env: `ANTHROPIC_API_KEY=your_key_here`"
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

    model_used = "anthropic" if anthropic_key else ("ollama" if ollama_url else "none")
    return {"reply": reply, "model_used": model_used}


if __name__ == "__main__":
    os.environ.setdefault('OMP_NUM_THREADS', '4')
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)