# OphthalmoAI - Eye Disease Screening

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1%2B-EE4C2C?logo=pytorch&logoColor=white)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Vite](https://img.shields.io/badge/Vite-7-646CFF?logo=vite&logoColor=white)](https://vite.dev/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind-3-38BDF8?logo=tailwindcss&logoColor=white)](https://tailwindcss.com/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![License](https://img.shields.io/badge/License-Apache%202.0-yellow.svg)](LICENSE)

A full-stack ophthalmology screening app for **7 visible eye conditions**. It uses a MobileNetV3 router, specialist EfficientNet-B4 models, Grad-CAM heatmaps, symptom checks, and a chat helper for follow-up eye-health questions.

> ⚕ **Medical Disclaimer:** OphthalmoAI is a research and educational screening tool. It is **not a substitute** for professional medical diagnosis, advice, or treatment. Always consult a qualified ophthalmologist.

---

## Table of Contents

- [Overview](#overview)
- [Live Demo Architecture](#live-demo-architecture)
- [Detectable Conditions](#detectable-conditions)
- [Model Architecture](#model-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Prerequisites](#prerequisites)
- [Quick Start (Docker)](#quick-start-docker)
- [Local Development Setup](#local-development-setup)
  - [1. Clone & Environment Setup](#1-clone--environment-setup)
  - [2. Dataset Preparation](#2-dataset-preparation)
  - [3. Model Training](#3-model-training)
  - [4. Backend Setup](#4-backend-setup)
  - [5. Frontend Setup](#5-frontend-setup)
- [Configuration (.env)](#configuration-env)
- [Running the Application](#running-the-application)
- [API Reference](#api-reference)
- [Features](#features)
- [Training Details](#training-details)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Troubleshooting](#troubleshooting)
- [Documentation](#documentation)
- [Contributing](#contributing)

---

## Overview

OphthalmoAI uses a **two-stage hierarchical inference pipeline**:

1. **Stage 1 - Router (MobileNetV3-Large):** Classifies the uploaded scan into one of three anatomical groups (Adnexal/Oculoplastic, Anterior Segment, or Ocular Surface). This lightweight model runs fast on CPU or GPU.

2. **Stage 2 - Specialist (EfficientNet-B4):** A dedicated specialist model for each anatomical group performs fine-grained disease classification within that group.

This layout is close to the way the project was trained: first route by eye region, then classify inside that smaller group. Keeping each specialist focused also makes the training data easier to reason about.

---

## Live Demo Architecture

```
Browser → React SPA (port 5173 dev / 8080 prod)
              ↓
          Nginx (prod only) → /api/* proxy
              ↓
      FastAPI Backend (port 8000)
              ↓
    ┌─────────────────────────┐
    │  PyTorch Inference      │
    │  MobileNetV3 (Router)   │
    │  EfficientNet-B4 × 3    │
    │  Grad-CAM               │
    └─────────────────────────┘
              ↓
    Google Gemini API  ← /chat endpoint
    or Ollama (local LLM)
```

---

## Detectable Conditions

| Condition | Anatomical Group | Severity |
|-----------|-----------------|----------|
| **Cataract** | Anterior Segment | Moderate–Severe |
| **Uveitis** | Anterior Segment | High - Sight-threatening |
| **Conjunctivitis** | Ocular Surface | Low (contagious) |
| **Jaundice** *(Scleral Icterus)* | Ocular Surface | High - Systemic emergency |
| **Pterygium** | Ocular Surface | Moderate |
| **Eyelid Conditions** *(Stye, Chalazion, Blepharitis)* | Adnexal/Oculoplastic | Low |
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
               Softmax Probabilities +
               Symptom Cross-Check +
               Clinical Report (PDF)
```

**Key architectural choices:**
- **EfficientNet-B4** - strong accuracy/compute tradeoff for image classification
- **WeightedRandomSampler** - helps with class imbalance
- **Gradient accumulation** (8 steps) - keeps training possible on 6 GB VRAM
- **Mixed precision (AMP)** - speeds up specialist training on CUDA
- **Grad-CAM** - shows which image regions affected the prediction

---

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| **Deep Learning** | PyTorch, EfficientNet-B4, MobileNetV3-Large | 2.1+ |
| **Explainability** | pytorch-grad-cam | ≥1.5.4 |
| **Backend** | FastAPI, Uvicorn, Pydantic | 0.110+ |
| **Image Processing** | Pillow, OpenCV (headless), NumPy | latest |
| **Rate Limiting** | slowapi | latest |
| **LLM Chat** | Google Gemini API *or* Ollama | latest |
| **Frontend** | React, Vite, Tailwind CSS | 19, 7, 3 |
| **PDF Reports** | jsPDF, jspdf-autotable | 4.x, 5.x |
| **Image Crop** | react-easy-crop | 5.x |
| **HTTP Client** | Axios | 1.x |
| **Container** | Docker, Docker Compose, Nginx | latest |
| **Orchestration** | Kubernetes (optional) | 1.28+ |

---

## Project Structure

```
OphthalmoAI/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI server, inference pipeline, chat endpoints
│   ├── medical_data.py      # Clinical info: descriptions, treatments, precautions
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx          # Main application (all pages + diagnostic tool)
│   │   ├── ChatBox.jsx      # AI Doctor floating chatbot component
│   │   ├── cropImage.js     # Canvas-based image crop utility
│   │   ├── index.css        # Design tokens, animations, global styles
│   │   └── main.jsx         # React entry point
│   ├── index.html
│   ├── nginx.conf           # Production Nginx config (proxy + SPA routing)
│   ├── package.json
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── vite.config.js
│   └── Dockerfile
│
├── scripts/
│   ├── train_router.py      # Stage 1: Train MobileNetV3 router
│   ├── train_anterior.py    # Stage 2: Train Anterior Segment specialist
│   ├── train_surface.py     # Stage 2: Train Ocular Surface specialist
│   ├── train_eyelid.py      # Stage 2: Single-class Adnexal helper
│   ├── verify_dataset.py    # Scan and remove corrupt images
│   ├── explore_data.py      # Visualise dataset distribution
│   └── check_setup.py       # Verify CUDA/PyTorch environment
│
├── models/                  # Trained .pth files (git-ignored)
│   ├── router.pth
│   ├── specialist_anterior.pth
│   ├── specialist_surface.pth
│   └── specialist_eyelid.pth
│
├── dataset/                 # Training data (git-ignored)
│   ├── Adnexal Oculoplastic/
│   │   └── Eyelid/
│   ├── Anterior Segment Pathology/
│   │   ├── Cataract/
│   │   └── Uveitis/
│   └── Ocular Surface Disorders/
│       ├── Conjunctivitis/
│       ├── Jaundice/
│       ├── Normal/
│       └── Pterygium/
│
├── k8s/                     # Kubernetes manifests
│   ├── namespace.yaml
│   ├── configmap.yaml
│   ├── secret.example.yaml
│   ├── backend-deployment.yaml
│   ├── backend-service.yaml
│   ├── frontend-deployment.yaml
│   ├── frontend-service.yaml
│   ├── ingress.yaml
│   └── kustomization.yaml
│
├── docs/                    # Project documentation
│   ├── PRD.md               # Product Requirements Document
│   ├── TRD.md                # Technical Requirements Document
│   ├── APP_FLOW.md           # Application Flow & User Journeys
│   ├── UI_UX_BRIEF.md        # Design System & UI/UX Brief
│   ├── BACKEND_SCHEMA.md     # API Schema & Data Models
│   ├── ROADMAP.md            # Deep technical roadmap
│   └── IMPLEMENTATION_PLAN.md # Setup & Implementation Checklist
│
├── docker-compose.yml
├── .env                     # API keys and config (git-ignored)
├── .env.example             # Template for .env
├── .gitignore
├── .dockerignore
├── PRODUCTION.md
├── ROADMAP.md
├── ISSUES.md
└── README.md
```

---

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| Python      | 3.10    | 3.11        |
| Node.js     | 18      | 22          |
| CUDA        | 12.1    | 12.4        |
| GPU VRAM    | 4 GB    | 6 GB (RTX 3050+) |
| RAM         | 8 GB    | 16 GB       |
| Disk (dataset + models) | 5 GB | 20 GB |

> **CPU-only mode** is supported but training will be significantly slower (~10–20×). Inference remains usable.

---

## Quick Start (Docker)

The fastest way to run OphthalmoAI without setting up Python locally.

```bash
git clone https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis.git
cd Eye-Disease-AI-Diagnosis

cp .env.example .env

docker compose up --build
```

Open **http://localhost:8080** in your browser.

> **Note:** The Docker image ships without trained model files. You must mount your `models/` directory or rebuild after training. See [PRODUCTION.md](PRODUCTION.md) for details.

---

## Local Development Setup

### 1. Clone & Environment Setup

```bash
git clone https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis.git
cd Eye-Disease-AI-Diagnosis

python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

**Install PyTorch with CUDA support** (do this first — do NOT use requirements.txt for torch):

```bash
# CUDA 12.4
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124

# CPU only (slower)
pip install torch torchvision
```

**Verify GPU is detected:**

```bash
python scripts/check_setup.py
```

**Install remaining backend dependencies:**

```bash
pip install -r backend/requirements.txt
```

---

### 2. Dataset Preparation

Organise your dataset to match this exact directory layout:

```
dataset/
├── Adnexal Oculoplastic/
│   └── Eyelid/              ← All eyelid condition images here
├── Anterior Segment Pathology/
│   ├── Cataract/
│   └── Uveitis/
└── Ocular Surface Disorders/
    ├── Conjunctivitis/
    ├── Jaundice/
    ├── Normal/
    └── Pterygium/
```

**Verify dataset integrity** (removes corrupt images before training):

```bash
python scripts/verify_dataset.py
```

**Explore dataset statistics and class distributions:**

```bash
python scripts/explore_data.py
```

---

### 3. Model Training

Train all models in sequence. Each script saves the best checkpoint automatically to `models/`.

**Stage 1 - Router model** (~15-30 min on GPU):

```bash
python scripts/train_router.py
```

**Stage 2 - Specialist models** (run in any order; ~60-120 min each on RTX 3050):

```bash
python scripts/train_anterior.py    # Cataract, Uveitis
python scripts/train_surface.py     # Conjunctivitis, Jaundice, Normal, Pterygium
python scripts/train_eyelid.py      # Eyelid helper; router handles final routing
```

> **Training notes:**
> - The Adnexal group only has one class. The app returns "Eyelid" directly when the router selects that group, so there is no multi-class eyelid specialist at inference time.
> - Gradient accumulation (8 steps, effective batch = 32) and mixed precision (AMP) are used to fit within 6 GB VRAM.
> - `WeightedRandomSampler` with `TARGET_SAMPLES_PER_CLASS = 5000` balances classes each epoch.
> - All models are fine-tuned from ImageNet pre-trained weights (`weights='DEFAULT'`).

---

### 4. Backend Setup

**Create a `.env` file** in the project root:

```bash
cp .env.example .env
```

**Start the FastAPI server:**

```bash
python backend/main.py
```

The API will be available at:
- **http://localhost:8000** - API root
- **http://localhost:8000/docs** - Interactive Swagger UI
- **http://localhost:8000/health** - Health check

---

### 5. Frontend Setup

```bash
cd frontend
npm install
```

**Optional — create a local environment file:**

```bash
# frontend/.env.local
VITE_API_URL=http://localhost:8000
```

**Start the development server:**

```bash
npm run dev
```

**Build for production:**

```bash
npm run build
```

---

## Configuration (.env)

Create a `.env` file in the **project root** (or copy `.env.example`):

```env
# LLM Chat Backend (choose one)
# Option A: Google Gemini (set key, leave OLLAMA_URL blank)
GEMINI_API_KEY=your-gemini-key-here
GEMINI_MODEL=gemini-2.0-flash

# Option B: Ollama (free, local)
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b

# Inference
FORCE_CPU=false        # Set to true to disable GPU for inference
MAX_FILE_SIZE_BYTES=20971520

# Server
CORS_ORIGINS=*                  # Comma-separated list of allowed origins
CORS_ALLOW_CREDENTIALS=false    # Must stay false while CORS_ORIGINS=*
PORT=8000
HOST=0.0.0.0
MODELS_DIR=./models    # Path to trained .pth files

# Rate limiting (requires slowapi)
PREDICT_RATE_LIMIT=10/minute
CHAT_RATE_LIMIT=30/minute
```

**Chat backend priority:** `GEMINI_API_KEY` → `OLLAMA_URL` → Setup instructions returned.

**VRAM guidance for Ollama on 6 GB GPU:**

| Model | VRAM | Notes |
|-------|------|-------|
| `llama3.2:1b` | ~1 GB | Fastest |
| `llama3.2:3b` | ~2.5 GB | Good default; leaves headroom |
| `llava:7b` | ~5 GB | ⚠ Tight |
| `llama3.1:8b` | ~5.5 GB | ⚠ Very tight |

> By default, the backend sets `"num_gpu": 0` for Ollama to avoid VRAM conflicts with PyTorch models. Remove this if you have sufficient VRAM.

> Get a Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey) — it's free for moderate usage.

---

## Running the Application

```bash
# Terminal 1 — Backend
python backend/main.py

# Terminal 2 — Frontend
cd frontend && npm run dev

# Terminal 3 — Ollama (if using local LLM)
ollama serve
```

Open **http://localhost:5173** in your browser.

---

## API Reference

### `GET /`
Returns system status, loaded models, and active chat backend.

### `GET /health`
Simple liveness check. Returns `{ "ok": true, "device": "cuda" }`.

### `GET /ready`
Readiness check — returns 503 if the router model is not loaded.

### `GET /conditions`
Returns clinical metadata for all 7 detectable conditions, sourced from `backend/medical_data.py`. The frontend's Conditions page consumes this endpoint directly, so the UI and the AI's clinical reference data can never drift out of sync.

### `POST /predict`

Accepts an eye scan and symptom data. Returns a full diagnostic result.

**Request** — `multipart/form-data`:

| Field | Type | Required | Values |
|-------|------|----------|--------|
| `file` | `File` | ✅ | JPG / PNG / BMP (max 20 MB by default) |
| `pain` | `string` | ✅ | `None` · `Mild` · `Severe` · `Not Sure` |
| `vision` | `string` | ✅ | `No` · `Yes` · `Not Sure` |
| `itch` | `string` | ✅ | `No` · `Yes` · `Not Sure` |
| `halos` | `string` | ❌ | `No` · `Yes` · `Not Sure` |
| `discharge` | `string` | ❌ | `None` · `Watery` · `Thick/Yellow` · `Not Sure` |
| `light_sens` | `string` | ❌ | `No` · `Yes` · `Not Sure` |
| `floaters` | `string` | ❌ | `No` · `Yes` · `Not Sure` |
| `duration` | `string` | ❌ | `<1 day` ... `>1 month` · `Not Sure` |

**Response:**
```json
{
  "group_name": "Ocular Surface Disorders",
  "diagnosis": "Conjunctivitis",
  "confidence": 94.7,
  "heatmap": "data:image/jpeg;base64,...",
  "probabilities": {
    "Conjunctivitis": 0.947,
    "Jaundice": 0.021,
    "Normal": 0.018,
    "Pterygium": 0.014
  },
  "hybrid_warnings": [
    "✅ Symptom Match: Itchiness strongly supports Allergic Conjunctivitis."
  ],
  "hybrid_warnings_structured": [
    { "severity": "info", "message": "Symptom Match: Itchiness strongly supports Allergic Conjunctivitis." }
  ],
  "details": {
    "description": "...",
    "analysis": "...",
    "symptoms": ["..."],
    "treatment": ["..."],
    "precautions": ["..."],
    "severity": "Low (usually self-limiting, but contagious)",
    "advice": "..."
  }
}
```

Errors (offline model, oversized/invalid file, inference failure) are now returned as proper HTTP status codes (`503`, `413`, `415`, `422`, `500`) with a `detail` field, rather than `200 OK` with an `error` key.

### `POST /chat`

Sends a message to the AI Doctor chatbot.

**Request** — `application/json`:
```json
{
  "message": "What does conjunctivitis mean?",
  "history": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi! How can I help?" }
  ],
  "diagnosis_context": { }
}
```

**Response:**
```json
{
  "reply": "Conjunctivitis (commonly called Pink Eye) is...",
  "model_used": "gemini"
}
```

Full schema documentation: [`docs/BACKEND_SCHEMA.md`](docs/BACKEND_SCHEMA.md)

---

## Features

| Feature | Description |
|---------|-------------|
| **Hierarchical Inference** | Two-stage pipeline: router → specialist, mirroring clinical triage |
| **Grad-CAM Heatmaps** | Visual attention maps showing which image regions drove the diagnosis |
| **Symptom Cross-Check** | Rule-based engine that validates AI diagnosis against all 8 reported symptoms |
| **Clinical Safety Alerts** | Flags dangerous diagnosis/symptom mismatches |
| **AI Doctor Chat** | Contextual ophthalmology Q&A powered by Google Gemini or Ollama |
| **4-page PDF report** | Report with scan, heatmap, differential diagnosis, treatment, and "Find a Doctor" links |
| **Text-to-Speech** | Reads the diagnosis and clinical advice aloud via the Web Speech API |
| **Image Crop Tool** | Built-in crop interface to focus on the ROI before analysis |
| **Find a Doctor** | One-click Google Maps link to find ophthalmologists nearby |
| **Medical News** | Curated eye health research articles |
| **Conditions Library** | Detailed clinical cards for all 7 detectable conditions, served live from the backend |
| **Rate Limiting** | `/predict` and `/chat` are protected against abuse via `slowapi` |

---

## Training Details

| Hyperparameter | Router | Specialists |
|---------------|--------|-------------|
| Architecture | MobileNetV3-Large | EfficientNet-B4 |
| Input size | 224 × 224 | 380 × 380 |
| Batch size | 32 | 4 (×8 accum. = 32 effective) |
| Optimiser | Adam (lr=1e-3) | AdamW (lr=1e-4, wd=1e-4) |
| Scheduler | StepLR (step=7, γ=0.1) | CosineAnnealingLR |
| Epochs | 25 | 25 |
| Mixed Precision | ❌ | ✅ (AMP) |
| Class Balancing | WeightedRandomSampler | WeightedRandomSampler |
| Virtual samples/epoch | 5000 × num_groups | 5000 × num_classes |
| Pre-training | ImageNet DEFAULT | ImageNet DEFAULT |

---

## Kubernetes Deployment

See [PRODUCTION.md](PRODUCTION.md) for full Kubernetes deployment instructions.

```bash
# Build images
docker build -t ophthalmoai-backend:latest -f backend/Dockerfile .
docker build -t ophthalmoai-frontend:latest -f frontend/Dockerfile --build-arg VITE_API_URL=/api .

# Deploy
kubectl apply -k k8s

# Check rollout
kubectl -n ophthalmoai rollout status deployment/backend
kubectl -n ophthalmoai rollout status deployment/frontend
kubectl -n ophthalmoai get pods,svc,ingress
```

---

## Troubleshooting

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: No module named 'torch'` | venv not activated or wrong torch install | Activate venv; reinstall with CUDA wheel |
| `Router model not found at models/router.pth` | Models not trained yet | Run `python scripts/train_router.py` |
| CUDA out of memory during training | Batch size too large | Reduce `BATCH_SIZE` to 2, increase `ACCUMULATION_STEPS` to 16 |
| Chat returns setup instructions | Neither API key nor Ollama URL set | Add `GEMINI_API_KEY` or `OLLAMA_URL` to `.env` |
| `Connection refused` on Ollama | Ollama not running | Run `ollama serve` in a separate terminal |
| Frontend can't reach backend | CORS or wrong `VITE_API_URL` | Set `VITE_API_URL=http://localhost:8000` in `frontend/.env.local`, or rely on the Vite dev proxy |
| Grad-CAM heatmap missing | Old `grad-cam` version | Run `pip install "grad-cam>=1.5.4"` |
| `readinessProbe` failing (K8s) | Models not in Docker image | Rebuild backend image after training; ensure `models/` is present |
| `RuntimeError: Invalid CORS configuration` on startup | `CORS_ORIGINS=*` combined with `CORS_ALLOW_CREDENTIALS=true` | Set explicit origins in `CORS_ORIGINS`, or leave `CORS_ALLOW_CREDENTIALS` unset/false |
| `429` from `/predict` or `/chat` | Rate limit hit | Wait, or raise `PREDICT_RATE_LIMIT` / `CHAT_RATE_LIMIT` in `.env` |

---

## Documentation

Additional project documentation is available in the [`docs/`](docs/) folder, plus two root-level planning documents:

| Document | Description |
|----------|-------------|
| [`ROADMAP.md`](ROADMAP.md) | Project-wide milestone roadmap (v1.1 → v3.1) |
| [`ISSUES.md`](ISSUES.md) | Consolidated bug/tech-debt tracker |
| [`docs/PRD.md`](docs/PRD.md) | Product Requirements Document |
| [`docs/TRD.md`](docs/TRD.md) | Technical Requirements Document |
| [`docs/APP_FLOW.md`](docs/APP_FLOW.md) | Application Flow & User Journeys |
| [`docs/UI_UX_BRIEF.md`](docs/UI_UX_BRIEF.md) | Design System & UI/UX Brief |
| [`docs/BACKEND_SCHEMA.md`](docs/BACKEND_SCHEMA.md) | API Schema & Data Models |
| [`docs/IMPLEMENTATION_PLAN.md`](docs/IMPLEMENTATION_PLAN.md) | Setup & Implementation Checklist |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | Deep technical roadmap (accuracy, modalities, enterprise readiness) |

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push to the branch: `git push origin feature/your-feature`
5. Open a Pull Request

Please follow conventional commits and ensure all linting passes (`npm run lint` in frontend).

---

## License

Apache License 2.0 — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [EfficientNet](https://arxiv.org/abs/1905.11946) — Tan & Le, Google Brain
- [Grad-CAM](https://arxiv.org/abs/1610.02391) — Selvaraju et al.
- [pytorch-grad-cam](https://github.com/jacobgil/pytorch-grad-cam) — Jacob Gildenblat
- [FastAPI](https://fastapi.tiangolo.com/) — Sebastián Ramírez
- [Google Gemini](https://ai.google.dev/) — AI Doctor chat backend
