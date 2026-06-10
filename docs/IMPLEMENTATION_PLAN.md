# Setup Checklist
## OphthalmoAI

---

## 1. Quick Checklist

Use this list to verify a complete local setup from scratch.

### Environment

- [ ] Python 3.10+ installed
- [ ] Node.js 18+ and npm installed
- [ ] Git installed
- [ ] CUDA 12.x driver installed (if using GPU)
- [ ] (Optional) Ollama installed from https://ollama.ai

### Repository

- [ ] `git clone https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis.git`
- [ ] `cd Eye-Disease-AI-Diagnosis`
- [ ] `python -m venv venv && source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
- [ ] `pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124`
- [ ] `python scripts/check_setup.py` → confirm GPU detected
- [ ] `pip install -r backend/requirements.txt`

### Dataset

- [ ] Dataset organised per the directory structure in README
- [ ] `python scripts/verify_dataset.py` → 0 corrupt images
- [ ] `python scripts/explore_data.py` → distributions look reasonable

### Model Training

- [ ] `python scripts/train_router.py` → `models/router.pth` saved
- [ ] `python scripts/train_anterior.py` → `models/specialist_anterior.pth` saved
- [ ] `python scripts/train_surface.py` → `models/specialist_surface.pth` saved
- [ ] `python scripts/train_eyelid.py` → `models/specialist_eyelid.pth` saved (optional — not used in inference)

### Backend

- [ ] `.env` file created in project root
- [ ] `ANTHROPIC_API_KEY` or `OLLAMA_URL` set in `.env`
- [ ] `python backend/main.py` starts without errors
- [ ] `curl http://localhost:8000/health` → `{"ok": true, ...}`
- [ ] `http://localhost:8000/docs` loads Swagger UI

### Frontend

- [ ] `cd frontend && npm install`
- [ ] `npm run dev` starts without errors
- [ ] `http://localhost:5173` loads the app
- [ ] Upload a test image → result returned
- [ ] Chat sends and receives a response

### Docker (optional)

- [ ] Docker Desktop installed and running
- [ ] `.env` populated with API keys
- [ ] `docker compose up --build`
- [ ] `http://localhost:8080` loads the app
- [ ] `http://localhost:8000/health` returns `{"ok": true}`

---

## 2. Build Notes

### Phase 1 — Infrastructure Setup (Day 1)

| Task | Owner | Status |
|------|-------|--------|
| Repository structure defined | Dev | ✅ Done |
| Python virtual environment + PyTorch install | Dev | ✅ Done |
| FastAPI skeleton with lifespan + CORS | Dev | ✅ Done |
| Vite + React + Tailwind setup | Dev | ✅ Done |
| Docker Compose (backend + frontend) | Dev | ✅ Done |
| `.gitignore` / `.dockerignore` | Dev | ✅ Done |

### Phase 2 — Model Architecture & Training (Days 2–5)

| Task | Owner | Status |
|------|-------|--------|
| Dataset directory structure defined | Dev | ✅ Done |
| `verify_dataset.py` + `explore_data.py` | Dev | ✅ Done |
| `train_router.py` (MobileNetV3, 3 classes) | Dev | ✅ Done |
| `train_anterior.py` (EfficientNet-B4, 2 classes) | Dev | ✅ Done |
| `train_surface.py` (EfficientNet-B4, 4 classes) | Dev | ✅ Done |
| `train_eyelid.py` (single-class helper) | Dev | ✅ Done |
| WeightedRandomSampler class balancing | Dev | ✅ Done |
| AMP mixed precision + gradient accumulation | Dev | ✅ Done |

### Phase 3 — Backend Inference API (Days 3–6)

| Task | Owner | Status |
|------|-------|--------|
| Model loading via lifespan context manager | Dev | ✅ Done |
| `/predict` endpoint — full inference pipeline | Dev | ✅ Done |
| Grad-CAM integration (pytorch-grad-cam) | Dev | ✅ Done |
| Heatmap → base64 JPEG encoding | Dev | ✅ Done |
| Symptom cross-check logic | Dev | ✅ Done |
| `MEDICAL_INFO` dictionary (7 conditions) | Dev | ✅ Done |
| `/chat` endpoint — Anthropic + Ollama support | Dev | ✅ Done |
| Ophthalmology system prompt | Dev | ✅ Done |
| `/health` and `/ready` probes | Dev | ✅ Done |
| GPU cache cleanup per request | Dev | ✅ Done |

### Phase 4 — Frontend Core (Days 4–8)

| Task | Owner | Status |
|------|-------|--------|
| Design system (tokens, fonts, Tailwind config) | Dev | ✅ Done |
| Navigation (5-tab SPA, mobile + desktop) | Dev | ✅ Done |
| Home page (hero, quick-access grid, features) | Dev | ✅ Done |
| DiagnosticPage — file upload + crop modal | Dev | ✅ Done |
| Symptom form (8 dropdowns) | Dev | ✅ Done |
| API call to `/predict` | Dev | ✅ Done |
| Result card (diagnosis, confidence, severity) | Dev | ✅ Done |
| Clinical alerts strip | Dev | ✅ Done |
| Heatmap toggle | Dev | ✅ Done |
| Tabbed detail panel (4 tabs) | Dev | ✅ Done |
| Probability bars (`<ProbabilityBar>`) | Dev | ✅ Done |
| TTS (Web Speech API) | Dev | ✅ Done |
| `ChatBox.jsx` — floating chat widget | Dev | ✅ Done |
| Quick question chips | Dev | ✅ Done |
| How It Works page | Dev | ✅ Done |
| Conditions page + modal | Dev | ✅ Done |
| Medical News page + category filter | Dev | ✅ Done |

### Phase 5 — PDF Report (Days 7–9)

| Task | Owner | Status |
|------|-------|--------|
| 4-page jsPDF layout | Dev | ✅ Done |
| Patient scan + heatmap images in PDF | Dev | ✅ Done |
| `autoTable` for symptoms, treatment, precautions | Dev | ✅ Done |
| Differential diagnosis bar chart | Dev | ✅ Done |
| Emergency signs section (Page 4) | Dev | ✅ Done |
| "Find an Ophthalmologist" links (Page 4) | Dev | ✅ Done |
| Clinical disclaimer footer (all pages) | Dev | ✅ Done |

### Phase 6 — Infrastructure & Production (Days 9–11)

| Task | Owner | Status |
|------|-------|--------|
| Backend Dockerfile (CPU torch wheel) | Dev | ✅ Done |
| Frontend Dockerfile (multi-stage build) | Dev | ✅ Done |
| Nginx config (proxy, SPA, cache, healthz) | Dev | ✅ Done |
| Docker Compose (healthchecks, depends_on) | Dev | ✅ Done |
| Kubernetes manifests (namespace, configmap, deployments, services, ingress) | Dev | ✅ Done |
| Kubernetes liveness + readiness probes | Dev | ✅ Done |

### Phase 7 — Documentation (Day 11–12)

| Task | Owner | Status |
|------|-------|--------|
| README.md | Dev | ✅ Done |
| PRODUCTION.md | Dev | ✅ Done |
| `docs/PRD.md` | Dev | ✅ Done |
| `docs/TRD.md` | Dev | ✅ Done |
| `docs/APP_FLOW.md` | Dev | ✅ Done |
| `docs/UI_UX_BRIEF.md` | Dev | ✅ Done |
| `docs/BACKEND_SCHEMA.md` | Dev | ✅ Done |
| `docs/IMPLEMENTATION_PLAN.md` | Dev | ✅ Done |

---

## 3. Known Issues & Recommended Fixes

These items are documented in the TRD but summarised here as actionable tasks.

### Issue 1 — Extra symptom fields not sent to API

**Location:** `frontend/src/App.jsx` — `handleAnalyze()`  
**Problem:** `halos`, `discharge`, `lightSens`, `spots`, `duration` are collected but only `pain`, `vision`, `itch` are sent to `/predict`. The extra fields are used in the PDF only.  
**Fix:**
1. Add new Form fields to the `/predict` FastAPI endpoint
2. Expand `analyze_symptoms()` to incorporate halos, discharge, light sensitivity rules
3. Update FormData in `handleAnalyze()` to include all 8 symptom fields

### Issue 2 — Unused `App.css` file

**Location:** `frontend/src/App.css`  
**Problem:** The file exists (Vite template artefact) but is never imported.  
**Fix:** Delete `frontend/src/App.css`. No functionality is affected.

### Issue 3 — No Vite proxy for development

**Location:** `frontend/vite.config.js`  
**Problem:** No proxy is configured. Developers must set `VITE_API_URL` manually or encounter CORS issues.  
**Fix:** Add to `vite.config.js`:
```javascript
server: {
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true,
      rewrite: (path) => path.replace(/^\/api/, '')
    }
  }
}
```
Then set `VITE_API_URL=/api` in `.env.local`.

### Issue 4 — No input image validation on backend

**Problem:** The backend does not validate file size, MIME type, or image dimensions before inference.  
**Fix:** Add at the start of `/predict`:
```python
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
contents = await file.read()
if len(contents) > MAX_FILE_SIZE:
    raise HTTPException(status_code=413, detail="File too large")
```

### Issue 5 — Single Uvicorn worker limits concurrency

**Problem:** Running one worker is safe for GPU (avoids model contention) but blocks concurrent requests.  
**Fix (medium term):** Implement a request queue with asyncio locks, or use a task queue (Celery + Redis) so multiple workers can share GPU access safely.

---

## 4. Future Roadmap (v2.0+)

### High Priority

| Feature | Notes |
|---------|-------|
| Expand symptom API | Send all 8 symptom fields to backend; expand cross-check rules |
| User accounts / history | Store scan results per user (requires DB: PostgreSQL + Prisma or SQLAlchemy) |
| Retinal fundus support | Add fundus image preprocessing + new specialist model for AMD/Glaucoma/DR |
| Mobile app | React Native or Capacitor wrapper |

### Medium Priority

| Feature | Notes |
|---------|-------|
| Multi-language | i18n for UI text; system prompt localisation |
| Confidence calibration | Temperature scaling post-training to calibrate softmax probabilities |
| Model versioning | Serve multiple model versions; A/B test routing |
| Offline mode | Service worker + cached models via ONNX/TFLite in browser |

### Low Priority / Research

| Feature | Notes |
|---------|-------|
| Federated learning | Train on distributed hospital data without centralising patient images |
| OCT / Fundus specialist | Extend to posterior segment pathology |
| DICOM support | Accept DICOM files from clinical scanners |
| EHR integration | FHIR API for exporting results to patient records |
| Batch inference API | Accept ZIP of images, return batch results as CSV |
