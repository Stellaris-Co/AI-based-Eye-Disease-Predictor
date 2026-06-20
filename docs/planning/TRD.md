# Technical Notes
## OphthalmoAI

---

## 1. System Overview

OphthalmoAI is split into two main pieces:

- **Backend:** Python / FastAPI serving a PyTorch inference pipeline via REST API
- **Frontend:** React SPA served by Nginx (production) or Vite dev server (development)

Communication is over HTTP/JSON (REST), with multipart/form-data for image uploads.

---

## 2. Technology Stack

### 2.1 Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | Python | 3.10+ (3.11 recommended) |
| Web framework | FastAPI | ≥0.110 |
| ASGI server | Uvicorn (with standard extras) | ≥0.29 |
| Deep learning | PyTorch + torchvision | 2.1+ |
| Model: Router | MobileNetV3-Large | torchvision |
| Model: Specialists | EfficientNet-B4 | torchvision |
| Explainability | pytorch-grad-cam | ≥1.5.4 |
| Image processing | Pillow, OpenCV-headless, NumPy | latest |
| LLM client | `anthropic` SDK (async) | ≥0.25 |
| HTTP client | `httpx` (async, for Ollama) | ≥0.27 |
| Validation | Pydantic v2 | ≥2.5 |
| Config | python-dotenv | ≥1.0 |
| Multipart | python-multipart | ≥0.0.9 |

### 2.2 Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Language | JavaScript (ES2020+) | — |
| Framework | React | 19 |
| Build tool | Vite | 7 |
| CSS | Tailwind CSS | 3 |
| CSS post-processing | PostCSS + Autoprefixer | 8.x |
| Icons | lucide-react | ≥0.554 |
| HTTP client | Axios | ≥1.13 |
| PDF generation | jsPDF + jspdf-autotable | 4.x, 5.x |
| Image crop | react-easy-crop | 5.x |
| Fonts | Sora, DM Sans (Google Fonts) | — |

### 2.3 Infrastructure

| Component | Technology |
|-----------|-----------|
| Containerisation | Docker, Docker Compose v2 |
| Frontend server (prod) | Nginx 1.27 (unprivileged) |
| Orchestration | Kubernetes ≥1.28 (optional) |
| Ingress | Nginx Ingress Controller (K8s) |

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
│  Routes:                                                         │
│    GET  /         → system status                                │
│    GET  /health   → liveness check                               │
│    GET  /ready    → readiness check (503 if models not loaded)   │
│    POST /predict  → inference pipeline                           │
│    POST /chat     → LLM chat proxy                               │
│                                                                  │
│  Inference Pipeline:                                             │
│    1. Preprocess (Resize → Normalize → Tensor)                   │
│    2. Router (MobileNetV3) → group_idx                           │
│    3. Specialist (EfficientNet-B4) → diagnosis + probs           │
│    4. Grad-CAM → heatmap (base64 JPEG)                           │
│    5. Symptom cross-check → hybrid_warnings                      │
│    6. Medical data lookup → details                              │
│                                                                  │
│  State: Models loaded at startup via lifespan context manager    │
│  Memory: GPU cache cleared after each prediction                 │
└──────────────────┬──────────────────────┬───────────────────────┘
                   │                      │
          ┌────────▼───────┐    ┌─────────▼─────────┐
          │ PyTorch Models │    │  LLM Backend       │
          │ (GPU / CPU)    │    │  Anthropic Claude  │
          │ router.pth     │    │  OR Ollama (local) │
          │ specialist_*.pth│   └────────────────────┘
          └────────────────┘
```

### 3.2 Inference Pipeline

```
POST /predict (multipart: file, pain, vision, itch)
        │
        ▼
1. Read file bytes → PIL Image → convert RGB
2. Preprocess:
   - Resize(380, 380)
   - ToTensor()
   - Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
   → input_tensor [1, 3, 380, 380]
        │
        ▼
3. Router (MobileNetV3-Large, no_grad):
   - Forward pass → logits [1, 3]
   - Softmax → router_probs
   - argmax → group_idx ∈ {0, 1, 2}
        │
        ├── group_idx == 0 (Adnexal): Direct pass-through
        │   → diagnosis = "Eyelid", confidence = router_conf × 100
        │   → probs_dict = {"Eyelid": 1.0}
        │   → heatmap = None
        │
        └── group_idx ∈ {1, 2} (Anterior / Surface):
            ├── Specialist forward (EfficientNet-B4, no_grad):
            │   → logits → softmax → class_idx, probs
            │   → diagnosis = classes[class_idx]
            │   → confidence = probs[class_idx] × 100
            │
            └── Grad-CAM (pytorch-grad-cam):
                - target_layer = model.features[-1]
                - grayscale_cam [1, 380, 380]
                - overlay on original image (RGB, float32 /255)
                - encode as base64 JPEG (quality 85)
                → heatmap_base64
        │
        ▼
5. analyze_symptoms(diagnosis, pain, vision, itch)
   → hybrid_warnings: List[str]
        │
        ▼
6. MEDICAL_INFO[diagnosis] → details dict
        │
        ▼
7. Return JSON response
```

---

## 4. Data Models

### 4.1 Inference Output

```python
{
  "group_name": str,           # e.g. "Ocular Surface Disorders"
  "diagnosis": str,            # e.g. "Conjunctivitis"
  "confidence": float,         # 0.0 – 100.0
  "heatmap": str | None,       # "data:image/jpeg;base64,..." or null
  "probabilities": dict,       # {"ClassName": float, ...} sums to ~1.0
  "hybrid_warnings": list[str],# Clinical alert strings
  "details": {
    "description": str,
    "analysis": str,
    "symptoms": list[str],
    "treatment": list[str],
    "precautions": list[str],
    "severity": str,
    "advice": str
  }
}
```

### 4.2 Chat Request / Response

```python
# Request
{
  "message": str,
  "history": [{"role": "user"|"assistant", "content": str}],
  "diagnosis_context": dict | None   # full /predict response
}

# Response
{
  "reply": str,
  "model_used": "anthropic" | "ollama" | "none"
}
```

---

## 5. Model Specifications

### 5.1 Router — MobileNetV3-Large

| Property | Value |
|----------|-------|
| Input | `[1, 3, 224, 224]` (after pre-processing at 380 → router resizes internally in training) |
| Pre-processing at inference | Resize(380,380) → ToTensor → Normalize (shared transform) |
| Output classes | 3 (Adnexal, Anterior, Ocular Surface) |
| Final layer | `classifier[3]` → `Linear(in, 3)` |
| Saved as | `models/router.pth` (state_dict) |
| Loaded with | `strict=False` (tolerates minor key mismatches) |

### 5.2 Specialist — EfficientNet-B4

| Property | Anterior | Surface |
|----------|----------|---------|
| Input | `[1, 3, 380, 380]` | `[1, 3, 380, 380]` |
| Output classes | 2 (Cataract, Uveitis) | 4 (Conjunctivitis, Jaundice, Normal, Pterygium) |
| Final layer | `classifier[1]` → `Linear(in, N)` | same |
| Grad-CAM target | `model.features[-1]` | same |
| Saved as | `models/specialist_anterior.pth` | `models/specialist_surface.pth` |

### 5.3 Adnexal — Direct Pass-Through

- Only one class (Eyelid) — no specialist model runs
- `specialist_eyelid.pth` can be trained for completeness, but it is not used for inference
- `SPECIALIST_MODELS[0]` has `type: "direct"` and returns Eyelid with router confidence

---

## 6. Performance Requirements

| Metric | GPU (RTX 3050, 6 GB) | CPU |
|--------|---------------------|-----|
| Router inference | ~50 ms | ~500 ms |
| Specialist inference | ~100 ms | ~2000 ms |
| Grad-CAM | ~200 ms | ~3000 ms |
| Total `/predict` response | <1 s | <10 s |
| `/chat` response (Claude) | 1–5 s | 1–5 s |
| `/chat` response (Ollama 3B) | 2–8 s | 20–60 s |

---

## 7. Security Requirements

| Requirement | Implementation |
|-------------|---------------|
| CORS | Configured via `CORS_ORIGINS` env var; default `*` (dev only) |
| No persistent storage | No database; no images stored server-side |
| Non-root containers | Backend: `appuser`; Frontend: Nginx unprivileged (uid 101) |
| Secrets | API keys only via environment variables; never in code or images |
| Rate limiting | Not implemented in v1.0 — recommended via reverse proxy (Nginx `limit_req`) |
| Input validation | File type check implicit via PIL; Pydantic validates chat request |
| `readOnlyRootFilesystem` | Disabled for backend (temp files needed); enabled for frontend |

---

## 8. Error Handling

| Scenario | Backend Behaviour | Frontend Behaviour |
|----------|------------------|-------------------|
| Router not loaded | Returns `{"error": "AI diagnostic system offline..."}` | `alert()` with error message |
| Specialist not loaded | Returns `{"error": "Specialist model for group X not loaded"}` | `alert()` |
| Invalid image file | PIL raises exception → caught → returns `{"error": "Analysis failed: ..."}` | `alert()` |
| Grad-CAM failure | `try/except` — heatmap set to `None`; rest of result still returned | Heatmap toggle hidden |
| Chat LLM error | Returns error message string in `reply` | Displayed as bot message |
| Network error (frontend) | — | `alert()` with error description |

---

## 9. Known Limitations & Technical Debt

| Item | Notes |
|------|-------|
| Extra symptom fields not sent to API | `halos`, `discharge`, `lightSens`, `spots`, `duration` are captured in the UI and included in PDF reports but are **not transmitted** to `/predict`. Only `pain`, `vision`, `itch` are used for backend cross-checking. Future work should expand the symptom API. |
| `App.css` is unused | `frontend/src/App.css` is a Vite template artefact. It is not imported anywhere and can be safely deleted. |
| No dev proxy in Vite config | `vite.config.js` does not configure a proxy for `/api`. Developers must set `VITE_API_URL` or rely on CORS. A proxy entry is recommended to avoid CORS in dev. |
| Single Uvicorn worker | Running one worker is safe for GPU (avoids model contention) but limits CPU concurrency. Consider a request queue (Celery/RQ) for high-traffic deployments. |
| Adnexal specialist is single-class | `train_eyelid.py` trains an MSE-loss model on the Eyelid class. The resulting `.pth` is not used at inference time because the router returns Eyelid directly. |
| No input image validation | The backend does not check file size, MIME type header, or image dimensions before inference. Large images slow inference; malformed files cause generic errors. |
