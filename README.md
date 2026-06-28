# OphthalmoAI — Eye Disease Screening

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1%2B-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-38BDF8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Azure](https://img.shields.io/badge/Azure-Ready-0078D4?logo=microsoftazure&logoColor=white)](https://azure.microsoft.com/)
[![CI](https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis/actions/workflows/ci.yml/badge.svg)](https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis/actions)
[![Security](https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis/actions/workflows/security.yml/badge.svg)](https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis/actions)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

A full-stack ophthalmology screening app for **7 visible eye conditions**. It uses a MobileNetV3 router, specialist EfficientNet-B4 models, Grad-CAM heatmaps, symptom cross-checks, and a chat helper for follow-up eye-health questions — deployable to **Azure** in minutes via the GitHub Student Developer Pack.

> ⚕ **Medical Disclaimer:** OphthalmoAI is a research and educational screening tool. It is **not a substitute** for professional medical diagnosis, advice, or treatment. Always consult a qualified ophthalmologist.

---

## Table of Contents

- [Overview](#overview)
- [Detectable Conditions](#detectable-conditions)
- [Model Architecture](#model-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start — Docker](#quick-start--docker)
- [Local Development Setup](#local-development-setup)
- [Configuration (.env)](#configuration-env)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Features](#features)
- [Training Details](#training-details)
- [Azure Deployment (GitHub Student Developer Pack)](#azure-deployment-github-student-developer-pack)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Security](#security)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [License](#license)

---

## Overview

OphthalmoAI uses a **two-stage hierarchical inference pipeline**:

1. **Stage 1 — Router (MobileNetV3-Large):** Classifies the uploaded scan into one of three anatomical groups (Adnexal/Oculoplastic, Anterior Segment, or Ocular Surface).

2. **Stage 2 — Specialist (EfficientNet-B4):** A dedicated fine-grained classifier for the detected anatomical group, with Grad-CAM visual explanation and calibrated confidence scores.

Additional safety layers include image quality assessment, MC-Dropout uncertainty estimation, symptom cross-checking, and automatic flagging for clinician review on uncertain or high-stakes results.

---

## Detectable Conditions

| Condition | Anatomical Group | Urgency |
|-----------|-----------------|---------|
| **Cataract** | Anterior Segment | Elective |
| **Uveitis** | Anterior Segment | 🔴 Urgent |
| **Conjunctivitis** | Ocular Surface | Non-urgent |
| **Jaundice** *(Scleral Icterus)* | Ocular Surface | 🔴 Emergency |
| **Pterygium** | Ocular Surface | Elective |
| **Eyelid Conditions** *(Stye, Chalazion, Blepharitis)* | Adnexal/Oculoplastic | Non-urgent |
| **Normal** | All Groups | None |

---

## Model Architecture

```
Input Image (380×380 px)
        │
        ▼
┌──────────────────────┐
│  Router              │  MobileNetV3-Large
│  (3 output classes)  │  224×224 px input
└──────────┬───────────┘
           │
     ┌─────┴──────────────────────────┐
     │              │                 │
     ▼              ▼                 ▼
 Adnexal       Anterior           Ocular
 (direct)      Segment            Surface
               │                   │
        ┌──────▼──────┐    ┌───────▼──────┐
        │ EfficientNet│    │ EfficientNet │
        │    B4       │    │    B4        │
        │ 2 classes   │    │ 4 classes    │
        └─────────────┘    └──────────────┘
                │                  │
                └────────┬─────────┘
                         ▼
               Grad-CAM Heatmap +
               Calibrated Confidence +
               MC-Dropout Uncertainty +
               IQA Warnings +
               Symptom Cross-Check +
               Clinical Codes (ICD-10 / SNOMED-CT) +
               PDF Report
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Deep Learning** | PyTorch, EfficientNet-B4, MobileNetV3 | 2.1+ |
| **Explainability** | pytorch-grad-cam | ≥1.5.4 |
| **Calibration** | Temperature Scaling (TemperatureScaler) | custom |
| **Uncertainty** | MC-Dropout | custom |
| **Backend** | FastAPI, Uvicorn, Pydantic v2 | 0.115+ |
| **Auth** | JWT (python-jose), bcrypt, RBAC | latest |
| **Database** | SQLAlchemy 2, SQLite (dev) / PostgreSQL (prod) | 2.0+ |
| **Rate Limiting** | slowapi | 0.1.9 |
| **Image Processing** | Pillow, OpenCV-headless, NumPy | latest |
| **LLM Chat** | Google Gemini API or Ollama | latest |
| **Frontend** | React 19, Vite 7, Tailwind CSS 3 | as listed |
| **PDF Reports** | jsPDF, jspdf-autotable | 4.x, 5.x |
| **Image Crop** | react-easy-crop | 5.x |
| **Security** | DOMPurify, slowapi, python-jose | latest |
| **Logging** | structlog (JSON) | 24.x |
| **Container** | Docker, Docker Compose, Nginx | latest |
| **Cloud** | Azure Container Apps / AKS | latest |

---

## Project Structure

```
OphthalmoAI/
├── backend/
│   ├── main.py              # FastAPI app — inference, auth, chat, audit
│   ├── auth.py              # JWT + RBAC, brute-force protection
│   ├── security.py          # Middleware, magic-byte validation, rate limits
│   ├── validators.py        # Email, password, SSRF-URL, prompt-injection
│   ├── db.py                # SQLAlchemy models (User, ScanResult, AuditLog, …)
│   ├── medical_data.py      # Clinical descriptions, treatments, precautions
│   ├── clinical_codes.py    # ICD-10, SNOMED-CT, urgency tiers
│   ├── calibration.py       # Temperature scaling for confidence calibration
│   ├── uncertainty.py       # MC-Dropout + human-review policy
│   ├── iqa.py               # Image Quality Assessment
│   ├── model_registry.py    # Model versioning & rollback
│   ├── audit.py             # Dual-sink audit logging
│   ├── storage.py           # S3-compatible encrypted image storage
│   ├── logging_config.py    # structlog configuration
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # All pages + diagnostic tool
│   │   ├── ChatBox.jsx      # AI Doctor chat widget (DOMPurify sanitised)
│   │   ├── cropImage.js     # Canvas crop utility
│   │   └── index.css        # Design tokens, animations
│   ├── nginx.conf
│   ├── vite.config.js       # Dev proxy, security-hardened
│   └── Dockerfile
├── scripts/
│   ├── train_router.py
│   ├── train_anterior.py
│   ├── train_surface.py
│   ├── train_eyelid.py
│   ├── calibrate_models.py  # Temperature scaling calibration
│   ├── evaluate_models.py   # Sensitivity/specificity/AUC/ECE report
│   ├── verify_dataset.py
│   ├── explore_data.py
│   └── check_setup.py
├── tests/backend/
│   └── test_clinical_grade.py
├── k8s/                     # Kubernetes / AKS manifests
├── infra/azure/             # Azure-specific IaC (Bicep / CLI scripts)
├── docs/
│   ├── planning/            # PRD, TRD, APP_FLOW, IMPLEMENTATION_PLAN
│   ├── design/              # UI_UX_BRIEF
│   ├── technical/           # BACKEND_SCHEMA
│   └── clinical/            # INTENDED_USE, CLINICAL_VALIDATION, CLINICAL_SAFETY
├── .github/workflows/
│   ├── ci.yml
│   ├── security.yml
│   └── azure-deploy.yml     # Azure Container Apps CD pipeline
├── docker-compose.yml
├── .env.example
├── PRODUCTION.md
├── AZURE_DEPLOY.md          # Step-by-step Azure hosting guide
├── ROADMAP.md
├── SECURITY_AUDIT.md
└── ISSUES.md
```

---

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python | 3.10 | 3.11 |
| Node.js | 18 | 22 |
| CUDA | 12.1 | 12.4 |
| GPU VRAM | 4 GB | 6 GB (RTX 3050+) |
| RAM | 8 GB | 16 GB |
| Disk (dataset + models) | 5 GB | 20 GB |

---

## Quick Start — Docker

```bash
git clone https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis.git
cd Eye-Disease-AI-Diagnosis
cp .env.example .env           # fill in GEMINI_API_KEY or OLLAMA_URL
docker compose up --build
```

Open **http://localhost:8080**.

> **Note:** The Docker image does not include trained model weights. Mount `models/` as a volume or rebuild after training (see Model Training below).

---

## Local Development Setup

### 1. Clone & Environment

```bash
git clone https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis.git
cd Eye-Disease-AI-Diagnosis
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
```

**Install PyTorch (CUDA 12.4):**
```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
python scripts/check_setup.py   # verify GPU detected
```

**Install remaining backend dependencies:**
```bash
pip install -r backend/requirements.txt
```

### 2. Dataset Preparation

```
dataset/
├── Adnexal Oculoplastic/
│   └── Eyelid/
├── Anterior Segment Pathology/
│   ├── Cataract/
│   └── Uveitis/
└── Ocular Surface Disorders/
    ├── Conjunctivitis/
    ├── Jaundice/
    ├── Normal/
    └── Pterygium/
```

```bash
python scripts/verify_dataset.py    # removes corrupt images
python scripts/explore_data.py      # visualise class distributions
```

### 3. Model Training

```bash
python scripts/train_router.py       # ~15–30 min on GPU → models/router.pth
python scripts/train_anterior.py     # ~60–90 min → models/specialist_anterior.pth
python scripts/train_surface.py      # ~90–120 min → models/specialist_surface.pth
python scripts/train_eyelid.py       # optional single-class helper
```

### 4. Calibrate & Evaluate

```bash
python scripts/calibrate_models.py   # writes models/calibration.json
python scripts/evaluate_models.py    # writes models/validation_report.json
```

### 5. Backend

```bash
cp .env.example .env                 # edit with your keys
python backend/main.py               # starts on http://localhost:8000
# Swagger UI: http://localhost:8000/docs
```

### 6. Frontend

```bash
cd frontend
npm install
npm run dev                          # starts on http://localhost:5173
```

---

## Configuration (.env)

See `.env.example` for the full list. Key variables:

```env
# LLM (choose one)
GEMINI_API_KEY=your-key
GEMINI_MODEL=gemini-2.0-flash
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Auth
JWT_SECRET_KEY=<32-byte hex — generate with: python -c "import secrets; print(secrets.token_hex(32))">
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=480

# Database
DATABASE_URL=sqlite:///./ophthalmoai.db     # dev
# DATABASE_URL=postgresql://user:pass@host:5432/ophthalmoai  # prod

# Inference
FORCE_CPU=false
MAX_FILE_SIZE_BYTES=20971520

# Networking
CORS_ORIGINS=http://localhost:5173          # comma-separated for prod
ENVIRONMENT=development                     # set to 'production' in prod
```

---

## Running the Application

```bash
# Terminal 1 — Backend
python backend/main.py

# Terminal 2 — Frontend
cd frontend && npm run dev

# Terminal 3 — Ollama (if using local LLM)
ollama serve && ollama pull llama3.2:3b
```

Open **http://localhost:5173**

---

## API Reference

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| `GET` | `/` | ❌ | System status |
| `GET` | `/health` | ❌ | Liveness probe |
| `GET` | `/ready` | ❌ | Readiness probe (503 if models not loaded) |
| `GET` | `/conditions` | ❌ | All 7 condition metadata from `medical_data.py` |
| `POST` | `/predict` | ❌ | Eye scan inference (rate-limited) |
| `POST` | `/chat` | ❌ | AI Doctor chat proxy (rate-limited) |
| `POST` | `/auth/register` | ❌ | Create patient account |
| `POST` | `/auth/token` | ❌ | Login → JWT |
| `POST` | `/auth/logout` | 🔒 | Revoke token (blacklist JTI) |
| `GET` | `/auth/me` | 🔒 | Current user profile |

Full schema: [`docs/technical/BACKEND_SCHEMA.md`](docs/technical/BACKEND_SCHEMA.md)

---

## Features

| Feature | Status |
|---------|--------|
| Hierarchical AI inference (Router → Specialist) | ✅ |
| Grad-CAM heatmap visualisation | ✅ |
| Confidence calibration (Temperature Scaling) | ✅ |
| MC-Dropout uncertainty estimation | ✅ |
| Image Quality Assessment gate | ✅ |
| Symptom cross-check (all 8 fields) | ✅ |
| Clinical codes (ICD-10, SNOMED-CT) | ✅ |
| Automatic human-review flagging | ✅ |
| JWT auth + RBAC (patient / clinician / admin) | ✅ |
| Brute-force lockout on login | ✅ |
| Token blacklist (logout) | ✅ |
| Prompt-injection filtering | ✅ |
| Audit log (DB + structured log) | ✅ |
| Model versioning & rollback | ✅ |
| 4-page PDF report export | ✅ |
| AI Doctor chat (Gemini / Ollama) | ✅ |
| Text-to-speech narration | ✅ |
| Medical news feed | ✅ |
| Conditions library (live from backend) | ✅ |
| Rate limiting (/predict + /chat) | ✅ |
| Azure Container Apps deployment | ✅ |

---

## Training Details

| Hyperparameter | Router | Specialists |
|---------------|--------|-------------|
| Architecture | MobileNetV3-Large | EfficientNet-B4 |
| Input size | 224 × 224 | 380 × 380 |
| Batch size (effective) | 32 | 32 (4 × 8 accum.) |
| Optimiser | Adam (lr=1e-3) | AdamW (lr=1e-4, wd=1e-4) |
| Scheduler | StepLR (step=7, γ=0.1) | CosineAnnealingLR |
| Epochs | 25 | 25 |
| Mixed Precision | ❌ | ✅ (AMP) |
| Class Balancing | WeightedRandomSampler | WeightedRandomSampler |
| Virtual samples/epoch | 5000 × num_groups | 5000 × num_classes |
| Pre-training | ImageNet DEFAULT | ImageNet DEFAULT |

---

## Azure Deployment (GitHub Student Developer Pack)

See **[AZURE_DEPLOY.md](AZURE_DEPLOY.md)** for the complete step-by-step guide.

**Quick summary:**

1. Activate your GitHub Student Developer Pack → claim $100 Azure credit at [azure.microsoft.com/free/students](https://azure.microsoft.com/free/students)
2. Push your trained models and run `az login`
3. Run `bash infra/azure/deploy.sh` — provisions ACR, Azure Container Apps, PostgreSQL Flexible Server, and wires everything together
4. GitHub Actions (`azure-deploy.yml`) automatically rebuilds and redeploys on every push to `main`

Estimated monthly cost on the Student credit: **~$25–40/month** for a CPU-only production stack.

---

## Kubernetes Deployment

```bash
# Build images
docker build -t ophthalmoai-backend:latest -f backend/Dockerfile .
docker build -t ophthalmoai-frontend:latest -f frontend/Dockerfile --build-arg VITE_API_URL=/api .

# Deploy
kubectl apply -k k8s

# Monitor
kubectl -n ophthalmoai rollout status deployment/backend
kubectl -n ophthalmoai get pods,svc,ingress
```

See [`PRODUCTION.md`](PRODUCTION.md) for full K8s + AKS instructions.

---

## Security

A full white-box security audit was conducted (see [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md)). All 20 findings (9 Critical/High, 7 Medium, 4 Low) have been remediated:

- JWT secret enforcement at startup
- Token blacklisting on logout
- Magic-byte file validation (no MIME spoofing)
- Safe error details (no stack traces to clients)
- HTTP security headers middleware (CSP, HSTS, X-Frame-Options, …)
- CORS wildcard blocked in production
- Fail-hard rate limiting
- XSS-safe chat renderer (DOMPurify)
- CI/CD security scanning (Bandit, Semgrep, Trivy, Gitleaks)

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: torch` | venv not active | Activate venv; reinstall CUDA wheel |
| `Router model not found` | Models not trained | Run `python scripts/train_router.py` |
| `RuntimeError: JWT_SECRET_KEY is still default` | Placeholder not changed | Generate with `python -c "import secrets; print(secrets.token_hex(32))"` and set in `.env` |
| `RuntimeError: CORS_ORIGINS=* is not permitted in production` | ENVIRONMENT=production with wildcard CORS | Set explicit origins in `CORS_ORIGINS` |
| `RuntimeError: OLLAMA_URL rejected: SSRF risk` | OLLAMA_URL resolves to private IP | Use a public endpoint, or set `ENVIRONMENT=development` for localhost |
| `429` from `/predict` or `/chat` | Rate limit hit | Raise `PREDICT_RATE_LIMIT` / `CHAT_RATE_LIMIT` in `.env` |
| Chat returns setup instructions | Neither API key nor Ollama URL set | Add `GEMINI_API_KEY` to `.env` |
| Grad-CAM heatmap missing | Old `grad-cam` version | `pip install "grad-cam>=1.5.4"` |
| Azure deployment 503 | Models not in container | Build image after training; check `MODELS_DIR` env var |

---

## Documentation

| Document | Description |
|----------|-------------|
| [`AZURE_DEPLOY.md`](AZURE_DEPLOY.md) | Step-by-step Azure hosting with GitHub Student Pack |
| [`PRODUCTION.md`](PRODUCTION.md) | Docker Compose + Kubernetes production guide |
| [`SECURITY_AUDIT.md`](SECURITY_AUDIT.md) | Full white-box security audit report |
| [`ROADMAP.md`](ROADMAP.md) | Technical upgrade roadmap |
| [`ISSUES.md`](ISSUES.md) | Bug and tech-debt tracker |
| [`docs/planning/PRD.md`](docs/planning/PRD.md) | Product Requirements Document |
| [`docs/planning/TRD.md`](docs/planning/TRD.md) | Technical Requirements Document |
| [`docs/planning/APP_FLOW.md`](docs/planning/APP_FLOW.md) | Application flow & user journeys |
| [`docs/planning/IMPLEMENTATION_PLAN.md`](docs/planning/IMPLEMENTATION_PLAN.md) | Setup & implementation checklist |
| [`docs/design/UI_UX_BRIEF.md`](docs/design/UI_UX_BRIEF.md) | Design system & UI/UX brief |
| [`docs/technical/BACKEND_SCHEMA.md`](docs/technical/BACKEND_SCHEMA.md) | API schema & data models |
| [`docs/clinical/INTENDED_USE.md`](docs/clinical/INTENDED_USE.md) | Intended use statement |
| [`docs/clinical/CLINICAL_VALIDATION.md`](docs/clinical/CLINICAL_VALIDATION.md) | Validation report template |
| [`docs/clinical/CLINICAL_SAFETY.md`](docs/clinical/CLINICAL_SAFETY.md) | Safety mechanisms |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Run tests: `pytest tests/backend/ -v`
4. Lint frontend: `cd frontend && npm run lint`
5. Commit: `git commit -m 'feat: your feature'`
6. Open a Pull Request

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

Copyright © 2026 Akash Kundu.

---

## Acknowledgements

- [EfficientNet](https://arxiv.org/abs/1905.11946) — Tan & Le, Google Brain
- [Grad-CAM](https://arxiv.org/abs/1610.02391) — Selvaraju et al.
- [pytorch-grad-cam](https://github.com/jacobgil/pytorch-grad-cam) — Jacob Gildenblat
- [Temperature Scaling](https://arxiv.org/abs/1706.04599) — Guo et al.
- [MC-Dropout Uncertainty](https://arxiv.org/abs/1506.02142) — Gal & Ghahramani
- [FastAPI](https://fastapi.tiangolo.com/) — Sebastián Ramírez
- [Google Gemini](https://ai.google.dev/) — AI Doctor chat backend
