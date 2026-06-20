# OphthalmoAI — Upgrade Roadmap

**Document scope:** Accuracy improvements, condition expansion, and production-hardening for OphthalmoAI.  
Each section is ordered by impact-to-effort ratio. Items marked 🔴 are critical blockers for any clinical context.

---

## 0. Fix Known Issues First (Zero-Effort Wins)

These are documented in `docs/TRD.md` but not yet resolved. Fix before anything else.

### 0.1 Send all 8 symptoms to `/predict`

`handleAnalyze()` in `App.jsx` only sends `pain`, `vision`, `itch`. The other five are silently dropped.

```python
# backend/main.py — expand the endpoint signature
@app.post("/predict")
async def predict(
    file: UploadFile = File(...),
    pain: str = Form(...),
    vision: str = Form(...),
    itch: str = Form(...),
    halos: str = Form(default="No"),
    discharge: str = Form(default="None"),
    light_sens: str = Form(default="No"),
    floaters: str = Form(default="No"),
    duration: str = Form(default="Not Sure"),
):
```

Then expand `analyze_symptoms()`:

```python
def analyze_symptoms(diagnosis, pain, vision, itch, halos, discharge, light_sens, floaters, duration):
    alerts = []
    # existing rules ...
    if halos == "Yes" and diagnosis == "Cataract":
        alerts.append("✅ Symptom Match: Halos strongly support Cataract diagnosis.")
    if floaters == "Yes" and diagnosis not in ["Uveitis", "Normal"]:
        alerts.append("⚠️ Floaters detected: Rule out Vitreous Detachment or Retinal Tear.")
    if light_sens == "Yes" and diagnosis == "Uveitis":
        alerts.append("🚨 Photophobia + Uveitis: Sight-threatening — immediate care required.")
    if discharge in ["Thick/Yellow"] and diagnosis == "Conjunctivitis":
        alerts.append("✅ Symptom Match: Purulent discharge confirms Bacterial Conjunctivitis.")
    if duration in [">1 month"] and diagnosis in ["Conjunctivitis", "Eyelid"]:
        alerts.append("⚠️ Chronic duration — rule out Chlamydial infection or Chalazion.")
    return alerts
```

### 0.2 Add Vite dev proxy

```js
// frontend/vite.config.js
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: path => path.replace(/^\/api/, ''),
    }
  }
}
```

### 0.3 Input validation on the backend 🔴

```python
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp"}

@app.post("/predict")
async def predict(file: UploadFile = File(...), ...):
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(413, "File exceeds 20 MB limit")
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported file type: {file.content_type}")
    # PIL parse to catch disguised non-images
    try:
        image = Image.open(io.BytesIO(contents)).convert("RGB")
    except Exception:
        raise HTTPException(422, "File is not a valid image")
```

### 0.4 Delete `frontend/src/App.css`

It is never imported and pollutes the codebase.

---

## 1. Model Accuracy Improvements

### 1.1 Replace Single Model with Ensemble + TTA

The single EfficientNet-B4 specialist is the biggest accuracy bottleneck. Train three complementary architectures and average their softmax outputs.

```python
# backend/inference.py
import torchvision.models as M

ENSEMBLE_CONFIGS = {
    "anterior": [
        {"arch": "efficientnet_b4",  "path": "models/anterior_effb4.pth",  "classes": 2},
        {"arch": "efficientnet_b2",  "path": "models/anterior_effb2.pth",  "classes": 2},
        {"arch": "convnext_small",   "path": "models/anterior_cnxt.pth",   "classes": 2},
    ],
    "surface": [
        {"arch": "efficientnet_b4",  "path": "models/surface_effb4.pth",   "classes": 4},
        {"arch": "efficientnet_b2",  "path": "models/surface_effb2.pth",   "classes": 4},
        {"arch": "convnext_small",   "path": "models/surface_cnxt.pth",    "classes": 4},
    ],
}

def ensemble_predict(models_list, tensor, device):
    all_probs = []
    with torch.no_grad():
        for model in models_list:
            logits = model(tensor)
            probs = torch.softmax(logits[0], dim=0)
            all_probs.append(probs)
    # Average ensemble
    mean_probs = torch.stack(all_probs).mean(dim=0)
    return mean_probs
```

Add Test-Time Augmentation (TTA) for the inference pass:

```python
TTA_TRANSFORMS = [
    transforms.Compose([transforms.Resize((380, 380)), transforms.ToTensor(), transforms.Normalize(...)]),
    transforms.Compose([transforms.Resize((380, 380)), transforms.RandomHorizontalFlip(p=1.0), transforms.ToTensor(), transforms.Normalize(...)]),
    transforms.Compose([transforms.Resize((400, 400)), transforms.CenterCrop(380), transforms.ToTensor(), transforms.Normalize(...)]),
]

def tta_predict(model, image_pil, device):
    probs_list = []
    for t in TTA_TRANSFORMS:
        tensor = t(image_pil).unsqueeze(0).to(device)
        with torch.no_grad():
            probs = torch.softmax(model(tensor)[0], dim=0)
        probs_list.append(probs)
    return torch.stack(probs_list).mean(dim=0)
```

Expected accuracy gain: **+3–6% top-1** with no additional data.

### 1.2 Confidence Calibration (Temperature Scaling) 🔴

Raw softmax probabilities from deep neural networks are systematically overconfident. A model saying "94.7% Conjunctivitis" is misleading in a clinical context. Temperature scaling fixes this with a single learned scalar `T`.

```python
# scripts/calibrate.py
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

class TemperatureScaler(nn.Module):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, x):
        return self.model(x) / self.temperature

def calibrate_model(model, val_loader, device):
    scaler = TemperatureScaler(model).to(device)
    optimizer = torch.optim.LBFGS([scaler.temperature], lr=0.01, max_iter=50)
    nll_criterion = nn.CrossEntropyLoss()

    logits_list, labels_list = [], []
    model.eval()
    with torch.no_grad():
        for inputs, labels in val_loader:
            logits_list.append(model(inputs.to(device)))
            labels_list.append(labels.to(device))

    logits = torch.cat(logits_list)
    labels = torch.cat(labels_list)

    def eval_closure():
        optimizer.zero_grad()
        loss = nll_criterion(logits / scaler.temperature, labels)
        loss.backward()
        return loss

    optimizer.step(eval_closure)
    print(f"Optimal temperature: {scaler.temperature.item():.4f}")
    return scaler.temperature.item()
```

Store the calibrated temperature per specialist in `models/calibration.json` and divide logits by it at inference time.

### 1.3 Uncertainty Quantification via MC Dropout

Replace the current hard argmax with a Monte Carlo Dropout estimate that surfaces model uncertainty:

```python
def mc_dropout_predict(model, tensor, n_passes=20):
    """Run N stochastic forward passes with dropout enabled."""
    model.train()  # enables dropout
    probs_mc = []
    with torch.no_grad():
        for _ in range(n_passes):
            logits = model(tensor)
            probs_mc.append(torch.softmax(logits[0], dim=0))
    model.eval()
    probs_stack = torch.stack(probs_mc)
    mean_probs = probs_stack.mean(dim=0)
    epistemic_uncertainty = probs_stack.var(dim=0).sum().item()  # total variance
    return mean_probs, epistemic_uncertainty
```

Add `"uncertainty": 0.032` to the `/predict` response. Flag anything above `0.15` as "Low Confidence — Seek In-Person Evaluation."

### 1.4 Image Quality Assessment (IQA) Gate 🔴

Reject or warn on blurry, dark, or non-eye images before inference. This is a major source of false diagnoses in the wild.

```python
# backend/iqa.py
import cv2
import numpy as np

def assess_image_quality(image_pil):
    """Returns (is_acceptable, issues)"""
    img = np.array(image_pil)
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)
    issues = []

    # Sharpness via Laplacian variance
    laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
    if laplacian_var < 80:
        issues.append("Image appears blurry (Laplacian variance too low).")

    # Brightness
    mean_brightness = gray.mean()
    if mean_brightness < 30:
        issues.append("Image is too dark.")
    elif mean_brightness > 230:
        issues.append("Image is overexposed.")

    # Check that image contains a roughly circular ROI (eye-like)
    circles = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, 20,
                                param1=50, param2=30, minRadius=20, maxRadius=200)
    if circles is None:
        issues.append("No circular iris/pupil region detected — may not be an eye image.")

    return len(issues) == 0, issues
```

Return `iqa_warnings` in the predict response. Do NOT block inference; just surface warnings.

### 1.5 Adopt a Medically Pre-Trained Backbone

Replace ImageNet-pretrained EfficientNet-B4 with **RETFound** (a foundation model pre-trained on 1.6M retinal images by UCL/Moorfields Eye Hospital) or **BioMedCLIP**. These dramatically improve transfer learning efficiency for ophthalmic tasks.

```python
# Fine-tune RETFound for your specialist tasks
# https://github.com/rmaphoh/RETFound_MAE
from models_vit import vit_large_patch16  # RETFound is ViT-L/16

def build_retfound_specialist(num_classes, checkpoint_path):
    model = vit_large_patch16(num_classes=num_classes, drop_path_rate=0.2, global_pool=True)
    checkpoint = torch.load(checkpoint_path, map_location='cpu')
    model.load_state_dict(checkpoint['model'], strict=False)
    model.head = nn.Linear(model.head.in_features, num_classes)
    return model
```

Expected gain: **+5–12% top-1** on ophthalmic conditions vs ImageNet init.

---

## 2. Condition Coverage Expansion

### 2.1 Current Gap Analysis

The current 7 conditions cover only the **external anterior eye**. The full clinical spectrum requires additional imaging modalities.

| Imaging Modality | Conditions Coverable | Current Status |
|---|---|---|
| External slit-lamp photo | Cataract, Conjunctivitis, Uveitis, Pterygium, Eyelid, Jaundice | ✅ Partial |
| Fundus photography | Diabetic Retinopathy, Glaucoma, AMD, Retinal Detachment, CRVO | ❌ Missing |
| OCT B-scan | Macular Hole, Epiretinal Membrane, DME, Choroidal Neovascularization | ❌ Missing |
| Corneal topography | Keratoconus, Corneal Dystrophies | ❌ Missing |
| Visual field | Glaucoma severity staging | ❌ Missing |

### 2.2 Fundus Photography Module (Highest Priority Expansion)

Diabetic Retinopathy alone affects 100M+ people. Add a new anatomical group to the hierarchy:

```python
# backend/main.py — expanded HIERARCHY
HIERARCHY = {
    0: {'name': 'Adnexal Oculoplastic',     'classes': ['Eyelid']},
    1: {'name': 'Anterior Segment',          'classes': ['Cataract', 'Uveitis']},
    2: {'name': 'Ocular Surface',            'classes': ['Conjunctivitis', 'Jaundice', 'Normal', 'Pterygium']},
    3: {'name': 'Posterior Segment (Fundus)','classes': ['Normal Fundus', 'DR_Mild', 'DR_Moderate', 'DR_Severe', 'DR_Proliferative', 'AMD_Dry', 'AMD_Wet', 'Glaucoma', 'CRVO', 'Retinal_Detachment']},
}
```

Add a fundus-specific preprocessing pipeline (fundus images need different normalization and often benefit from CLAHE preprocessing):

```python
import cv2

def preprocess_fundus(image_pil):
    """Apply CLAHE to fundus images to enhance vessel and lesion contrast."""
    img = np.array(image_pil)
    lab = cv2.cvtColor(img, cv2.COLOR_RGB2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l_eq = clahe.apply(l)
    lab_eq = cv2.merge([l_eq, a, b])
    enhanced = cv2.cvtColor(lab_eq, cv2.COLOR_LAB2RGB)
    return Image.fromarray(enhanced)
```

Training dataset sources: **EyePACS**, **APTOS 2019**, **IDRiD**, **ORIGA/REFUGE** (all publicly available on Kaggle).

### 2.3 DR Severity Grading (International Scale)

```python
# backend/medical_data.py additions
DR_GRADING = {
    'DR_Mild':          {'grade': 1, 'icdcode': 'E11.3291', 'urgency': 'Schedule within 3 months'},
    'DR_Moderate':      {'grade': 2, 'icdcode': 'E11.3391', 'urgency': 'Schedule within 1 month'},
    'DR_Severe':        {'grade': 3, 'icdcode': 'E11.3491', 'urgency': 'Refer within 1 week'},
    'DR_Proliferative': {'grade': 4, 'icdcode': 'E11.3591', 'urgency': '🚨 URGENT — same-day ophthalmologist'},
}
```

### 2.4 Keratoconus Detection (Corneal Group)

```python
HIERARCHY[4] = {
    'name': 'Corneal Pathology',
    'classes': ['Normal Cornea', 'Keratoconus_Early', 'Keratoconus_Advanced', 'Corneal_Scar', 'Bullous_Keratopathy'],
    'model_file': 'specialist_corneal.pth',
    'preprocessing': 'standard'  # or 'clahe' for topography images
}
```

Dataset: **Kaggle Keratoconus Dataset**, **AREDS2**.

### 2.5 Additional Conditions Within Existing Groups

Expand the current groups without new modalities:

**Anterior Segment additions:**
- `Glaucoma_Suspect` (from disc appearance in anterior photo)
- `Corneal_Ulcer` (slit-lamp)
- `Hypopyon` (pus in anterior chamber)
- `Hyphema` (blood in anterior chamber)

**Ocular Surface additions:**
- `Dry_Eye_Disease` (staining patterns)
- `Subconjunctival_Hemorrhage`
- `Episcleritis` vs `Scleritis` differentiation

---

## 3. Industrial-Grade Backend Architecture

### 3.1 Async Inference Queue (Critical for Production) 🔴

The current single-request synchronous model blocks the event loop and can't handle concurrent users. Inference on CPU takes 5–10s; multiple users will time out.

```
Request → FastAPI → Celery Task Queue → Redis → GPU Worker Pool → Result Cache → Response
```

```python
# backend/worker.py
from celery import Celery
import redis

app = Celery('ophthalmoai', broker='redis://localhost:6379/0', backend='redis://localhost:6379/1')

@app.task(bind=True, max_retries=3)
def run_inference(self, image_bytes: bytes, symptoms: dict, task_id: str):
    try:
        result = _inference_pipeline(image_bytes, symptoms)
        return result
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2)
```

```python
# backend/main.py — async endpoint
@app.post("/predict/async")
async def predict_async(file: UploadFile = File(...), ...):
    contents = await file.read()
    task = run_inference.delay(contents, symptoms)
    return {"task_id": task.id, "status": "queued"}

@app.get("/predict/result/{task_id}")
async def get_result(task_id: str):
    task = run_inference.AsyncResult(task_id)
    if task.state == "PENDING":
        return {"status": "processing"}
    elif task.state == "SUCCESS":
        return {"status": "complete", "result": task.result}
    else:
        return {"status": "failed", "error": str(task.info)}
```

### 3.2 Authentication & Authorization 🔴

Add JWT-based auth with role-based access:

```python
# backend/auth.py
from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from passlib.context import CryptContext
from enum import Enum

class UserRole(str, Enum):
    PATIENT = "patient"
    CLINICIAN = "clinician"
    ADMIN = "admin"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)):
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid or expired token")

def require_role(*roles: UserRole):
    def dep(token: dict = Depends(verify_token)):
        if token.get("role") not in [r.value for r in roles]:
            raise HTTPException(403, "Insufficient permissions")
        return token
    return dep

# Usage
@app.post("/predict")
async def predict(..., user = Depends(require_role(UserRole.PATIENT, UserRole.CLINICIAN))):
    ...

# Admin-only model management
@app.post("/admin/models/reload")
async def reload_models(admin = Depends(require_role(UserRole.ADMIN))):
    ...
```

### 3.3 Database Layer (PostgreSQL + SQLAlchemy) 🔴

Add persistence for scan history, audit trails, and user management:

```python
# backend/models/db.py
from sqlalchemy import Column, String, Float, JSON, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base
import uuid

Base = declarative_base()

class ScanResult(Base):
    __tablename__ = "scan_results"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    diagnosis = Column(String(100), nullable=False)
    confidence = Column(Float, nullable=False)
    uncertainty = Column(Float, nullable=True)
    group_name = Column(String(100))
    probabilities = Column(JSON)
    symptoms_reported = Column(JSON)
    hybrid_warnings = Column(JSON)
    model_version = Column(String(20), nullable=False)
    temperature = Column(Float)           # calibration temperature used
    tta_enabled = Column(Boolean, default=False)
    ensemble_count = Column(Integer, default=1)
    iqa_score = Column(Float)             # image quality score
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    reviewed_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    clinician_notes = Column(Text, nullable=True)
    # Image stored as S3/GCS path, never raw bytes
    image_path = Column(String(500), nullable=True)
    heatmap_path = Column(String(500), nullable=True)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True))
    action = Column(String(100))          # "predict", "chat", "login", "export_pdf"
    resource_id = Column(UUID(as_uuid=True), nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(String(500))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    success = Column(Boolean)
    error_detail = Column(Text, nullable=True)
```

### 3.4 Rate Limiting with slowapi 🔴

```python
# backend/main.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address, storage_uri="redis://localhost:6379")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/predict")
@limiter.limit("10/minute")       # 10 scans per minute per IP
async def predict(request: Request, ...):
    ...

@app.post("/chat")
@limiter.limit("30/minute")
async def chat_endpoint(request: Request, ...):
    ...
```

### 3.5 Model Versioning & Rollback

```python
# backend/model_registry.py
import json
from pathlib import Path

MODEL_REGISTRY = Path("models/registry.json")

def register_model(group: str, arch: str, path: str, metrics: dict):
    registry = json.loads(MODEL_REGISTRY.read_text()) if MODEL_REGISTRY.exists() else {}
    if group not in registry:
        registry[group] = []
    registry[group].append({
        "version": f"v{len(registry[group]) + 1}",
        "arch": arch,
        "path": path,
        "metrics": metrics,   # {"val_acc": 0.91, "auc": 0.96, "calibration_ece": 0.03}
        "registered_at": datetime.utcnow().isoformat(),
        "active": False
    })
    MODEL_REGISTRY.write_text(json.dumps(registry, indent=2))

def get_active_model(group: str) -> dict:
    registry = json.loads(MODEL_REGISTRY.read_text())
    return next((m for m in registry.get(group, []) if m["active"]), None)
```

### 3.6 API Versioning

```python
# backend/main.py
from fastapi import APIRouter

v1 = APIRouter(prefix="/v1")
v2 = APIRouter(prefix="/v2")

@v1.post("/predict")  # legacy response format
@v2.post("/predict")  # extended response with uncertainty, IQA, ICD-10 codes

app.include_router(v1)
app.include_router(v2)
```

---

## 4. Clinical Accuracy & Safety Features

### 4.1 Differential Diagnosis with ICD-10 Codes

Add ICD-10 codes and clinical urgency triage to the response:

```python
# backend/medical_data.py additions
CLINICAL_METADATA = {
    'Cataract':       {'icd10': 'H26.9',  'urgency': 'routine',   'referral': 'ophthalmologist'},
    'Conjunctivitis': {'icd10': 'H10.9',  'urgency': 'non-urgent','referral': 'GP or optometrist'},
    'Uveitis':        {'icd10': 'H20.9',  'urgency': 'urgent',    'referral': 'uveitis specialist'},
    'Jaundice':       {'icd10': 'R17',    'urgency': 'emergency',  'referral': 'internal medicine'},
    'Pterygium':      {'icd10': 'H11.009','urgency': 'elective',   'referral': 'ophthalmologist'},
    'Eyelid':         {'icd10': 'H00.019','urgency': 'non-urgent', 'referral': 'GP or ophthalmologist'},
    'Normal':         {'icd10': 'Z01.01', 'urgency': 'none',       'referral': 'routine screening'},
}
```

### 4.2 Second-Opinion Request Mechanism

When confidence is below a threshold or uncertainty is high, flag for human review:

```python
CONFIDENCE_THRESHOLD = 0.75

def needs_human_review(confidence: float, uncertainty: float, diagnosis: str) -> bool:
    critical = ['Uveitis', 'Jaundice', 'DR_Proliferative', 'Retinal_Detachment']
    if confidence < CONFIDENCE_THRESHOLD:
        return True
    if uncertainty > 0.15:
        return True
    if diagnosis in critical and confidence < 0.90:
        return True
    return False
```

Add to response: `"requires_human_review": true, "review_reason": "Confidence below threshold for high-severity condition."`

### 4.3 Report Tamper Detection

Add a cryptographic signature to PDF reports so they can be verified as unmodified:

```python
import hashlib, hmac

def sign_report(report_data: dict, secret_key: str) -> str:
    payload = json.dumps(report_data, sort_keys=True).encode()
    signature = hmac.new(secret_key.encode(), payload, hashlib.sha256).hexdigest()
    return signature

# Embed signature in PDF footer and expose a /verify endpoint
@app.post("/verify-report")
async def verify_report(scan_id: str, signature: str):
    result = await db.get_scan(scan_id)
    expected_sig = sign_report(result, REPORT_SECRET)
    return {"valid": hmac.compare_digest(signature, expected_sig)}
```

---

## 5. Observability & Monitoring Stack

### 5.1 Structured Logging

Replace `print()` statements throughout with structured JSON logging:

```python
# backend/logging_config.py
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(),
    ]
)

logger = structlog.get_logger()

# In predict endpoint
logger.info("inference.complete",
    diagnosis=result["diagnosis"],
    confidence=result["confidence"],
    model_version=MODEL_VERSION,
    latency_ms=elapsed * 1000,
    user_id=user.id,
    device=str(DEVICE),
)
```

### 5.2 Prometheus Metrics

```python
# backend/metrics.py
from prometheus_client import Counter, Histogram, Gauge, make_asgi_app
import time

INFERENCE_COUNTER = Counter("ophthalmoai_inferences_total", "Total predictions", ["diagnosis", "group"])
INFERENCE_LATENCY = Histogram("ophthalmoai_inference_duration_seconds", "Inference latency")
CONFIDENCE_HISTOGRAM = Histogram("ophthalmoai_confidence", "Prediction confidence", buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 1.0])
GPU_MEMORY_GAUGE = Gauge("ophthalmoai_gpu_memory_used_bytes", "GPU memory in use")

# Expose /metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# In predict:
start = time.perf_counter()
# ... inference ...
elapsed = time.perf_counter() - start
INFERENCE_COUNTER.labels(diagnosis=result["diagnosis"], group=result["group_name"]).inc()
INFERENCE_LATENCY.observe(elapsed)
CONFIDENCE_HISTOGRAM.observe(result["confidence"] / 100)
```

### 5.3 Model Drift Detection

Log prediction distributions over time and alert when they shift significantly (indicating distribution shift in real-world data):

```python
# backend/drift_monitor.py
import numpy as np
from scipy.stats import ks_2samp

def check_distribution_drift(reference_probs: list, current_probs: list, threshold=0.05):
    """Kolmogorov-Smirnov test for distribution shift."""
    stat, p_value = ks_2samp(reference_probs, current_probs)
    drift_detected = p_value < threshold
    return {"drift_detected": drift_detected, "ks_statistic": stat, "p_value": p_value}
```

Store rolling 24-hour prediction distributions per class in Redis and run nightly drift checks.

### 5.4 Recommended Monitoring Stack (Docker Compose)

```yaml
# docker-compose.monitoring.yml
services:
  prometheus:
    image: prom/prometheus:latest
    volumes: ["./monitoring/prometheus.yml:/etc/prometheus/prometheus.yml"]
    ports: ["9090:9090"]

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    ports: ["3000:3000"]
    volumes: ["grafana-data:/var/lib/grafana"]

  loki:
    image: grafana/loki:latest
    ports: ["3100:3100"]

  sentry:
    image: sentry:latest
    environment:
      SENTRY_SECRET_KEY: "${SENTRY_SECRET_KEY}"
    ports: ["9000:9000"]
```

---

## 6. Compliance & Security (Clinical-Grade) 🔴

### 6.1 HIPAA Technical Safeguards Checklist

| Safeguard | Requirement | Implementation |
|---|---|---|
| Access Control | Unique user ID per person | JWT with `user_id` claim |
| Audit Controls | Log all PHI access | `AuditLog` DB table + Loki |
| Integrity | Protect PHI from alteration | Report HMAC signature |
| Transmission Security | Encrypt PHI in transit | TLS 1.3 (Nginx, not self-signed) |
| Encryption at Rest | Encrypt stored images | S3 SSE-KMS or pgcrypto |
| Minimum Necessary | Only access what's needed | RBAC roles |
| BAA | Agreement with cloud providers | AWS/GCP HIPAA BAA |

### 6.2 Image Storage Security

**Never store uploaded images on the local filesystem.** Use object storage with encryption:

```python
# backend/storage.py
import boto3
from botocore.config import Config

s3 = boto3.client("s3",
    config=Config(signature_version="s3v4"),
    region_name="us-east-1"
)

def upload_scan(image_bytes: bytes, scan_id: str, user_id: str) -> str:
    key = f"scans/{user_id}/{scan_id}.jpg"
    s3.put_object(
        Bucket=BUCKET_NAME,
        Key=key,
        Body=image_bytes,
        ContentType="image/jpeg",
        ServerSideEncryption="aws:kms",
        KMSKeyId=KMS_KEY_ID,
        Metadata={"scan_id": scan_id, "user_id": user_id},
    )
    return key  # Store path in DB, never raw image

def get_presigned_url(key: str, expires_in=300) -> str:
    return s3.generate_presigned_url("get_object",
        Params={"Bucket": BUCKET_NAME, "Key": key},
        ExpiresIn=expires_in
    )
```

### 6.3 Security Headers (Nginx)

```nginx
# frontend/nginx.conf additions
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; connect-src 'self' https://api.anthropic.com;" always;
add_header Permissions-Policy "camera=(self), microphone=()" always;
add_header X-Permitted-Cross-Domain-Policies "none" always;
```

---

## 7. CI/CD Pipeline

### 7.1 GitHub Actions Workflow

```yaml
# .github/workflows/main.yml
name: OphthalmoAI CI/CD

on: [push, pull_request]

jobs:
  backend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: {python-version: '3.11'}
      - run: pip install -r backend/requirements.txt
      - run: pip install pytest pytest-asyncio httpx
      - run: pytest tests/backend/ -v --tb=short

  frontend-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: {node-version: '22'}
      - run: cd frontend && npm ci
      - run: cd frontend && npm run lint
      - run: cd frontend && npm run build  # catches compile errors

  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: pip install pip-audit
      - run: pip-audit -r backend/requirements.txt --desc on
      - run: cd frontend && npm audit --audit-level=high

  docker-build:
    needs: [backend-test, frontend-test, security-scan]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: docker compose build
      - run: docker scout cves ophthalmoai-backend:latest
      - name: Push to registry
        if: github.ref == 'refs/heads/main'
        run: |
          docker tag ophthalmoai-backend:latest $REGISTRY/ophthalmoai-backend:${{ github.sha }}
          docker push $REGISTRY/ophthalmoai-backend:${{ github.sha }}
```

### 7.2 Test Structure

```
tests/
├── backend/
│   ├── test_predict.py           # inference with mock model
│   ├── test_symptoms.py          # all symptom cross-check rules
│   ├── test_iqa.py               # image quality gating
│   ├── test_auth.py              # JWT validation
│   ├── test_rate_limiting.py
│   └── test_calibration.py
└── frontend/
    ├── App.test.jsx              # component rendering
    └── api.test.js               # axios mock tests
```

---

## 8. Frontend Improvements

### 8.1 Patient History Dashboard

Add a "My Scans" page pulling from the authenticated user's scan history:

```jsx
const HistoryPage = () => {
  const [scans, setScans] = useState([])
  useEffect(() => {
    axios.get('/v2/scans/history', { headers: { Authorization: `Bearer ${token}` }})
      .then(r => setScans(r.data.scans))
  }, [])
  // Render timeline of past diagnoses with trends
}
```

### 8.2 Offline Mode with ONNX

Export models to ONNX and run in-browser via ONNX Runtime Web for offline screening:

```python
# scripts/export_onnx.py
import torch.onnx

def export_model(model, output_path, input_size=(1, 3, 380, 380)):
    dummy = torch.randn(*input_size)
    torch.onnx.export(
        model, dummy, output_path,
        export_params=True,
        opset_version=17,
        input_names=["image"],
        output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}}
    )
    print(f"Exported to {output_path}")
```

```js
// frontend/src/inference.worker.js — runs in Web Worker
import * as ort from 'onnxruntime-web'

let session = null
export async function loadModel() {
  session = await ort.InferenceSession.create('/models/specialist_surface.onnx')
}

export async function predict(imageTensor) {
  const feeds = { image: new ort.Tensor('float32', imageTensor, [1, 3, 380, 380]) }
  const results = await session.run(feeds)
  return results.logits.data
}
```

### 8.3 Real-Time Symptom Checker (Before Upload)

Add a pre-scan symptom triage that directs urgency before the user uploads anything:

```jsx
const TriageTool = () => {
  const [answers, setAnswers] = useState({})
  const urgencyScore = computeUrgency(answers) // local rule engine
  return (
    <div>
      {urgencyScore >= 8 && (
        <Alert color="red">
          Your symptoms suggest an EMERGENCY — go to A&E now, do not wait for AI analysis.
        </Alert>
      )}
    </div>
  )
}
```

### 8.4 Clinician Portal

A separate authenticated view for ophthalmologists to review, confirm, or override AI diagnoses:

```jsx
const ClinicianPortal = () => (
  <div className="grid grid-cols-12 gap-6">
    <PatientQueue />           {/* pending reviews */}
    <ScanReview />             {/* AI result + override UI */}
    <DiagnosisStats />         {/* model accuracy vs clinician corrections */}
  </div>
)
```

---

## 9. FHIR & EHR Integration

For hospital deployment, expose a FHIR R4 API so results can flow into patient records:

```python
# backend/fhir.py
from fhir.resources.observation import Observation
from fhir.resources.coding import Coding
import datetime

def result_to_fhir(scan_result: dict, patient_id: str) -> dict:
    obs = Observation.construct(
        status="final",
        code={"coding": [Coding.construct(
            system="http://snomed.info/sct",
            code=SNOMED_CODES.get(scan_result["diagnosis"], "246575002"),
            display=scan_result["diagnosis"]
        )]},
        subject={"reference": f"Patient/{patient_id}"},
        effectiveDateTime=datetime.datetime.utcnow().isoformat(),
        valueString=f"AI Screening: {scan_result['diagnosis']} ({scan_result['confidence']:.1f}% confidence)",
        component=[{
            "code": {"coding": [{"system": "http://loinc.org", "code": "88040-1"}]},
            "valueQuantity": {"value": scan_result["confidence"], "unit": "%"}
        }]
    )
    return obs.dict()

@app.get("/fhir/Observation/{scan_id}")
async def get_fhir_observation(scan_id: str, user=Depends(require_role(UserRole.CLINICIAN))):
    scan = await db.get_scan(scan_id)
    return result_to_fhir(scan, scan.user_id)
```

---

## 10. Prioritized Implementation Order

| Priority | Item | Estimated Effort | Accuracy/Safety Impact |
|---|---|---|---|
| P0 — Now | Fix known TRD issues (all 8 symptoms, input validation, rate limiting) | 1–2 days | High |
| P0 — Now | Confidence calibration (temperature scaling) | 1 day | Very High (clinical honesty) |
| P0 — Now | Image Quality Assessment gate | 1 day | High |
| P1 — Week 1 | Authentication + JWT + RBAC | 3–4 days | Required for production |
| P1 — Week 1 | PostgreSQL + audit logging | 2–3 days | Required for compliance |
| P1 — Week 2 | Ensemble (3 models per specialist) + TTA | 3–5 days training + 1 dev | +4–8% accuracy |
| P1 — Week 2 | MC Dropout uncertainty + human review flag | 1 day | High safety |
| P2 — Month 1 | Fundus photography group + DR grading | 1–2 weeks | Massive coverage expansion |
| P2 — Month 1 | Async Celery queue + Redis | 2–3 days | Required for scale |
| P2 — Month 1 | RETFound backbone fine-tuning | 1 week training | +8–12% accuracy |
| P2 — Month 1 | Prometheus + Grafana monitoring | 1–2 days | Operational maturity |
| P3 — Month 2 | Structured logging + drift detection | 2–3 days | Long-term reliability |
| P3 — Month 2 | ONNX export + offline mode | 3–4 days | Accessibility |
| P3 — Month 3 | FHIR R4 API | 1–2 weeks | Hospital deployability |
| P3 — Month 3 | Clinician portal | 1–2 weeks | Clinical trust loop |

---

## Appendix: Key Resources

| Resource | Link |
|---|---|
| RETFound Foundation Model | github.com/rmaphoh/RETFound_MAE |
| EyePACS (DR dataset) | kaggle.com/c/diabetic-retinopathy-detection |
| APTOS 2019 | kaggle.com/c/aptos2019-blindness-detection |
| IDRiD (DR + grading) | ieee-dataport.org/open-access/indian-diabetic-retinopathy-image-dataset-idrid |
| REFUGE (Glaucoma) | refuge.grand-challenge.org |
| Temperature Scaling paper | arxiv.org/abs/1706.04599 |
| MC Dropout uncertainty | arxiv.org/abs/1506.02142 |
| pytorch-grad-cam (current) | github.com/jacobgil/pytorch-grad-cam |
| FHIR R4 Python | github.com/nazrulworld/fhir.resources |
| slowapi (rate limiting) | github.com/laurentS/slowapi |
| structlog | structlog.readthedocs.io |
