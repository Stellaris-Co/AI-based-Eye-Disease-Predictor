# Technical Notes
## OphthalmoAI — v2.1

---

## 1. System Overview

OphthalmoAI is split into two main pieces:

- **Backend:** Python / FastAPI serving a PyTorch inference pipeline via REST API, with JWT auth, SQLAlchemy persistence, and structured logging.
- **Frontend:** React SPA served by Nginx (production) or Vite dev server (development).

Communication is over HTTP/JSON (REST), with `multipart/form-data` for image uploads.

---

## 2. Technology Stack

### 2.1 Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.10+ (3.11 recommended) |
| Web framework | FastAPI | ≥0.115 |
| ASGI server | Uvicorn (with standard extras) | ≥0.32 |
| Deep learning | PyTorch + torchvision | 2.1+ |
| Model: Router | MobileNetV3-Large | torchvision |
| Model: Specialists | EfficientNet-B4 | torchvision |
| Explainability | pytorch-grad-cam | ≥1.5.4 |
| Calibration | TemperatureScaler (custom) | `backend/calibration.py` |
| Uncertainty | MC-Dropout (custom) | `backend/uncertainty.py` |
| Image Quality Assessment | OpenCV-headless + PIL | `backend/iqa.py` |
| Clinical codes | ICD-10 / SNOMED-CT lookup | `backend/clinical_codes.py` |
| Image processing | Pillow, OpenCV-headless, NumPy | latest |
| Authentication | python-jose (JWT), passlib (bcrypt) | ≥3.3, ≥1.7.4 |
| Database ORM | SQLAlchemy | 2.0+ |
| Database | SQLite (dev) / PostgreSQL (prod) | — |
| LLM client | google-generativeai (Gemini) | ≥0.8 |
| HTTP client | httpx (async, for Ollama) | ≥0.28 |
| Validation | Pydantic v2 | ≥2.5 |
| Config | python-dotenv | ≥1.0 |
| Rate limiting | slowapi | 0.1.9 |
| Logging | structlog | 24.x |
| Model registry | SQLAlchemy + JSON sidecar | `backend/model_registry.py` |
| Encrypted storage | boto3 (S3-compatible) | optional |

### 2.2 Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | JavaScript (ES2020+) | — |
| Framework | React | 19 |
| Build tool | Vite | 7 |
| CSS | Tailwind CSS | 3 |
| Icons | lucide-react | ≥0.554 |
| HTTP client | Axios | ≥1.13 |
| PDF generation | jsPDF + jspdf-autotable | 4.x, 5.x |
| Image crop | react-easy-crop | 5.x |
| HTML sanitisation | DOMPurify | 3.x |
| Fonts | Sora, DM Sans (Google Fonts) | — |

### 2.3 Infrastructure

| Component | Technology |
|-----------|-----------|
| Containerisation | Docker, Docker Compose v2 |
| Frontend server (prod) | Nginx 1.27 (unprivileged) |
| Cloud | Azure Container Apps + ACR + PostgreSQL Flexible Server |
| Orchestration (optional) | Kubernetes ≥1.28 / AKS |
| Ingress | Nginx Ingress Controller (K8s) / Azure built-in HTTPS (ACA) |
| CI/CD | GitHub Actions (ci.yml + security.yml + azure-deploy.yml) |

---

## 3. Architecture

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│  Client Browser                                                  │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  React SPA (Vite/Nginx)                                   │  │
│  │  Pages: Home | Diagnostic | How It Works | Conditions | News │  │
│  │  Components: DiagnosticPage | ChatBot | CropTool | PDF    │  │
│  └───────────────────────┬───────────────────────────────────┘  │
└──────────────────────────┼──────────────────────────────────────┘
                           │  HTTP (REST + multipart)
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (Uvicorn)                                       │
│                                                                  │
│  Security Middleware Stack:                                      │
│    SecurityHeadersMiddleware → RequestIDMiddleware → CORS        │
│                                                                  │
│  Routes:                                                         │
│    GET  /           → system status                              │
│    GET  /health     → liveness probe                             │
│    GET  /ready      → readiness probe (503 if models not loaded) │
│    GET  /conditions → condition metadata from MEDICAL_INFO       │
│    POST /predict    → inference pipeline (rate-limited)          │
│    POST /chat       → LLM chat proxy (rate-limited)              │
│    POST /auth/register                                           │
│    POST /auth/token → JWT login                                  │
│    POST /auth/logout → JTI blacklist                             │
│    GET  /auth/me                                                 │
│                                                                  │
│  Inference Pipeline (POST /predict):                             │
│    1. Magic-byte validation + dimension check (IQA gate 1)       │
│    2. PIL decode → RGB                                           │
│    3. Image Quality Assessment (iqa.py) → iqa_warnings          │
│    4. Preprocess → [1, 3, 380, 380] tensor                      │
│    5. Router (MobileNetV3) → group_idx + router_conf            │
│    6. Specialist (EfficientNet-B4) → logits                     │
│    7. Temperature scaling (calibration.py) → calibrated probs   │
│    8. MC-Dropout (uncertainty.py) → epistemic_uncertainty       │
│    9. Grad-CAM → heatmap base64                                  │
│   10. Symptom cross-check → hybrid_warnings (8 fields)          │
│   11. Clinical codes (clinical_codes.py) → ICD-10, urgency      │
│   12. Human-review flag (uncertainty.py) → requires_human_review│
│   13. Persist to DB (ScanResult) + AuditLog                     │
│   14. Return JSON response                                       │
│                                                                  │
│  State: Models loaded at startup via lifespan context manager    │
│  DB: SQLAlchemy (SQLite dev, PostgreSQL prod)                    │
└──────────┬──────────────────────┬───────────────────────────────┘
           │                      │
  ┌────────▼───────┐    ┌─────────▼──────────┐
  │ PyTorch Models │    │  LLM Backend        │
  │ (GPU / CPU)    │    │  Google Gemini      │
  │ router.pth     │    │  OR Ollama (local)  │
  │ specialist_*.pth│   └────────────────────┘
  └────────────────┘
```

---

## 4. Data Models (DB)

### 4.1 User

```python
id, email, hashed_password, full_name,
role ("patient"|"clinician"|"admin"),
is_active, created_at, last_login_at
```

### 4.2 ScanResult

```python
id, user_id, diagnosis, confidence, group_name,
probabilities (JSON), calibrated, calibration_temperature,
uncertainty, requires_human_review, review_reasons (JSON),
icd10_code, snomed_code, urgency, urgency_rank,
hybrid_warnings (JSON), hybrid_warnings_structured (JSON),
iqa_acceptable, iqa_warnings (JSON),
symptoms_reported (JSON), model_version_id,
router_group_idx, image_path, heatmap_path, created_at
```

### 4.3 ClinicianOverride

```python
id, scan_id, clinician_id,
verdict ("agree"|"disagree"|"inconclusive"|"insufficient_image_quality"),
corrected_diagnosis, corrected_icd10, notes, created_at
```

### 4.4 AuditLog

```python
id, user_id, action, resource_id, resource_type,
ip_address, user_agent, success, error_detail,
metadata_ (JSON), timestamp
```

### 4.5 ModelVersion

```python
id, group_key, version_tag, architecture, weights_path,
val_accuracy, val_auc, val_sensitivity, val_specificity,
val_set_description, calibration_temperature, calibration_ece,
active, registered_at, registered_by
```

### 4.6 Inference Response (JSON)

```python
{
  "group_name": str,
  "diagnosis": str,
  "confidence": float,         # 0–100, calibrated
  "heatmap": str | None,       # "data:image/jpeg;base64,..."
  "probabilities": dict,       # {ClassName: float} sums to ~1.0
  "hybrid_warnings": list[str],
  "hybrid_warnings_structured": list[{"severity": str, "message": str}],
  "details": {                 # from MEDICAL_INFO
    "description", "analysis", "symptoms",
    "treatment", "precautions", "severity", "advice"
  },
  # New in v2.1:
  "calibrated": bool,
  "calibration_temperature": float,
  "uncertainty": float,
  "requires_human_review": bool,
  "review_reasons": list[str],
  "icd10_code": str,
  "snomed_code": str,
  "urgency": str,              # "none"|"elective"|"non-urgent"|"urgent"|"emergency"
  "urgency_rank": int,         # 0–4
  "referral": str,
  "escalation_message": str | None,
  "iqa_acceptable": bool,
  "iqa_warnings": list[str],
  "scan_id": str | None        # present if PERSIST_SCANS=true
}
```

---

## 5. Model Specifications

### 5.1 Router — MobileNetV3-Large

| Property | Value |
|----------|-------|
| Pre-processing input | Resize(380,380) → ToTensor → Normalize (shared transform) |
| Output classes | 3 (Adnexal, Anterior, Ocular Surface) |
| Final layer | `classifier[3]` → `Linear(in, 3)` |
| Saved as | `models/router.pth` (state_dict) |

### 5.2 Specialist — EfficientNet-B4

| Property | Anterior | Surface |
|----------|----------|---------|
| Input | `[1, 3, 380, 380]` | `[1, 3, 380, 380]` |
| Output classes | 2 (Cataract, Uveitis) | 4 (Conjunctivitis, Jaundice, Normal, Pterygium) |
| Calibration | Temperature scaling (models/calibration.json) | same |
| Uncertainty | MC-Dropout (8 passes default) | same |
| Grad-CAM target | `model.features[-1]` | same |

### 5.3 Adnexal — Direct Pass-Through

- Single class (Eyelid) — no specialist model needed at inference
- Router confidence is returned directly
- `SPECIALIST_MODELS[0]` has `type: "direct"`

---

## 6. Performance

| Metric | GPU (RTX 3050, 6 GB) | CPU |
|--------|---------------------|-----|
| Router inference | ~50 ms | ~500 ms |
| Specialist inference | ~100 ms | ~2000 ms |
| Temperature scaling | <1 ms | <1 ms |
| MC-Dropout (8 passes) | ~200 ms | ~3000 ms |
| Grad-CAM | ~200 ms | ~3000 ms |
| IQA check | ~30 ms | ~100 ms |
| Total `/predict` | <1 s | <10 s |
| `/chat` (Gemini) | 1–5 s | 1–5 s |

---

## 7. Security

| Requirement | Implementation |
|-------------|---------------|
| JWT auth | python-jose, HS256, configurable expiry |
| Token revocation | JTI-based in-memory blacklist (TokenBlacklist) |
| Role-based access | patient / clinician / admin; `require_role()` FastAPI dep |
| Brute-force protection | LoginAttemptTracker: 5 failures → 15-min lockout |
| CORS | Explicit origin list required in production; wildcard blocked |
| File validation | Magic-byte check + dimension guard (no MIME spoofing) |
| Upload size | Configurable `MAX_FILE_SIZE_BYTES` (default 20 MB) |
| Security headers | SecurityHeadersMiddleware: CSP, HSTS (prod), X-Frame-Options, etc. |
| Error messages | safe_error_detail(): no stack traces in production |
| Prompt injection | sanitise_chat_message(): 13 regex patterns blocked |
| SSRF | validate_ollama_url(): private IP ranges blocked |
| IP anonymisation | Last IPv4 octet / last 80 IPv6 bits masked in all logs |
| Audit trail | Every auth, prediction, and override logged to DB + structlog |
| Rate limiting | slowapi; raises RuntimeError at startup in production if absent |
| Container security | Non-root users; read-only filesystem (frontend) |

---

## 8. Error Handling

| Scenario | HTTP Status | Response |
|----------|------------|----------|
| Router not loaded | 503 | `{"detail": "AI diagnostic system offline..."}` |
| Specialist not loaded | 503 | `{"detail": "Specialist model for group X not loaded"}` |
| File too large | 413 | `{"detail": "File exceeds the X MB limit"}` |
| Invalid MIME type | 415 | `{"detail": "Unsupported file type '...'"}` |
| Magic byte mismatch | 415 | `{"detail": "Content-Type mismatch..."}` |
| Not a valid image | 422 | `{"detail": "File could not be decoded as an image"}` |
| Inference failure | 500 | `{"detail": "An internal error occurred (ref: <id>)"}` (production) |
| Rate limit exceeded | 429 | Standard slowapi response |
| Invalid credentials | 401 | `{"detail": "Invalid email or password."}` |
| Locked out | 401 | `{"detail": "Account temporarily locked..."}` |
| Insufficient permissions | 403 | `{"detail": "Your role ('...') does not have permission..."}` |
| Grad-CAM failure | 200 | `heatmap: null`; rest of result still returned |

---

## 9. Known Limitations & Technical Debt

| Item | Status |
|------|--------|
| Single Uvicorn worker limits CPU concurrency | Open — Celery/RQ queue planned for v3.1 |
| In-memory TokenBlacklist lost on restart | Open — Redis migration documented in ROADMAP.md |
| In-memory LoginAttemptTracker not shared across workers | Open — same Redis fix |
| `specialist_eyelid.pth` trained but unused at inference | Open — documented in ISSUES.md M7 |
| No input image validation beyond size/type | Resolved — magic-byte + dimension checks added |
| All 8 symptoms not sent to `/predict` | Resolved — all 8 fields now in FormData and backend |
| No Vite dev proxy | Resolved — added in vite.config.js |
| Conditions page used hardcoded data | Resolved — fetches from `GET /conditions` |
| `App.css` leftover | Resolved — removed |
| JWT secret placeholder in production | Resolved — startup guard added |
| CORS wildcard in production | Resolved — startup guard added |
| Stack traces leaked in 500 errors | Resolved — safe_error_detail() |
| Chat XSS risk | Resolved — DOMPurify sanitisation in ChatBox |
| No CI/CD | Resolved — ci.yml + security.yml + azure-deploy.yml |
| License inconsistency (MIT vs Apache) | Resolved — all references updated to Apache 2.0 |

For the full remediation history, see [`SECURITY_AUDIT.md`](../SECURITY_AUDIT.md).
