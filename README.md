# OphthalmoAI — AI-Powered Eye Disease Detection

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.1%2B-EE4C2C?logo=pytorch)](https://pytorch.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](https://react.dev/)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

A full-stack, AI-powered ophthalmology screening application that detects **7 eye conditions** using a **hierarchical deep learning pipeline** — a MobileNetV3 router followed by specialist EfficientNet-B4 models — with Grad-CAM visual explanations, symptom cross-checking, and an integrated AI doctor chatbot.

> ⚕ **Medical Disclaimer:** OphthalmoAI is a research and educational tool. It is **not a substitute** for professional medical diagnosis, advice, or treatment. Always consult a qualified ophthalmologist.

---

## Table of Contents

- [Overview](#overview)
- [Detectable Conditions](#detectable-conditions)
- [Model Architecture](#model-architecture)
- [Project Structure](#project-structure)
- [Tech Stack](#tech-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
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
- [Troubleshooting](#troubleshooting)

---

## Overview

OphthalmoAI uses a **two-stage hierarchical inference pipeline**:

1. **Stage 1 — Router (MobileNetV3-Large):** Classifies the uploaded scan into one of three anatomical groups (Adnexal/Oculoplastic, Anterior Segment, or Ocular Surface). This lightweight model runs fast on CPU or GPU.

2. **Stage 2 — Specialist (EfficientNet-B4):** A dedicated specialist model for each anatomical group performs fine-grained disease classification within that group.

This approach mirrors clinical ophthalmology practice where a triage step precedes subspecialist assessment. It also allows each specialist model to train on focused, relevant data rather than all 7 classes simultaneously, improving accuracy.

---

## Detectable Conditions

| Condition | Anatomical Group | Severity |
|-----------|-----------------|----------|
| **Cataract** | Anterior Segment | Moderate–Severe |
| **Uveitis** | Anterior Segment | High — Sight-Threatening |
| **Conjunctivitis** | Ocular Surface | Low (contagious) |
| **Jaundice** *(Scleral Icterus)* | Ocular Surface | High — Systemic Emergency |
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
     ┌─────┴─────────────────────┐
     │           │               │
     ▼           ▼               ▼
 Adnexal    Anterior         Ocular
 Group      Segment          Surface
            │                │
     ┌──────▼─────┐  ┌───────▼──────┐
     │ EfficientNet│  │ EfficientNet │
     │    B4       │  │    B4        │
     │ 2 classes   │  │ 4 classes    │
     └─────────────┘  └─────────────┘
           │                 │
           └────────┬────────┘
                    ▼
          Grad-CAM Heatmap +
          Softmax Probabilities +
          Symptom Cross-Check
```

**Key architectural choices:**
- **EfficientNet-B4** — superior accuracy/compute ratio for medical imaging
- **WeightedRandomSampler** — handles class imbalance without oversampling artifacts
- **Gradient Accumulation** (8 steps) — enables effective batch size of 32 on 6 GB VRAM
- **Mixed Precision (AMP)** — ~40% faster training with minimal accuracy loss
- **Grad-CAM** — produces visual attention maps showing which image regions drove the prediction

---

## Project Structure

```
OphthalmoAI/
├── backend/
│   ├── __init__.py
│   ├── main.py              # FastAPI server, inference pipeline, chat endpoints
│   └── medical_data.py      # Clinical info: descriptions, treatments, precautions
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── App.jsx          # Main application with hero, diagnostic tool, sections
│   │   ├── ChatBox.jsx      # AI Doctor floating chatbot
│   │   ├── cropImage.js     # Canvas-based image crop utility
│   │   ├── index.css        # Design tokens, animations, global styles
│   │   └── main.jsx         # React entry point
│   ├── index.html
│   ├── package.json
│   ├── tailwind.config.js
│   └── vite.config.js
│
├── scripts/
│   ├── train_router.py      # Stage 1: Train MobileNetV3 router
│   ├── train_anterior.py    # Stage 2: Train Anterior Segment specialist
│   ├── train_surface.py     # Stage 2: Train Ocular Surface specialist
│   ├── train_eyelid.py      # Stage 2: Train Adnexal specialist
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
├── .env                     # API keys and config (git-ignored)
├── .gitignore
├── backend/requirements.txt
└── README.md
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Deep Learning** | PyTorch 2.1+, EfficientNet-B4, MobileNetV3-Large |
| **Explainability** | pytorch-grad-cam (Grad-CAM) |
| **Backend** | FastAPI, Uvicorn, Pydantic |
| **Image Processing** | Pillow, OpenCV (headless), NumPy |
| **LLM Chat** | Anthropic Claude API *or* Ollama (llama3.2:3b) |
| **Frontend** | React 19, Vite 7, Tailwind CSS 3 |
| **PDF Reports** | jsPDF, jspdf-autotable |
| **HTTP Client** | Axios |
| **Image Crop** | react-easy-crop |

---

## Prerequisites

- **Python** 3.10+
- **Node.js** 18+ and npm
- **CUDA 12.4** compatible GPU (recommended: ≥ 6 GB VRAM) or CPU fallback
- **Git**

---

## Installation

### 1. Clone & Environment Setup

```bash
git clone https://github.com/AkashKundu114/Eye-Disease-AI-Diagnosis.git
cd Eye-Disease-AI-Diagnosis

python -m venv venv
venv\Scripts\activate
source venv/bin/activate
```

**Install PyTorch with CUDA support first** (do not use requirements.txt for this):

```bash
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu124
```

**Verify GPU detection:**

```bash
python scripts/check_setup.py
```

**Install remaining backend dependencies:**

```bash
pip install -r backend/requirements.txt
```

---

### 2. Dataset Preparation

Organise your dataset to match this directory layout:

```
dataset/
├── Adnexal Oculoplastic/
│   └── Eyelid/          ← All eyelid condition images here
├── Anterior Segment Pathology/
│   ├── Cataract/
│   └── Uveitis/
└── Ocular Surface Disorders/
    ├── Conjunctivitis/
    ├── Jaundice/
    ├── Normal/
    └── Pterygium/
```

**Verify dataset integrity** (removes corrupt images):

```bash
python scripts/verify_dataset.py
```

**Explore dataset statistics and samples:**

```bash
python scripts/explore_data.py
```

---

### 3. Model Training

Train all models in sequence. Each saves the best checkpoint automatically.

**Stage 1 — Router model** (runs quickly, ~15–30 min on GPU):

```bash
python scripts/train_router.py
```

**Stage 2 — Specialist models** (run in any order; each ~60–120 min on RTX 3050):

```bash
python scripts/train_anterior.py

python scripts/train_surface.py

python scripts/train_eyelid.py
```

> **Training notes:**
> - The Adnexal group (Eyelid only) has a single class, so `train_eyelid.py` uses MSE loss as a placeholder — the router handles routing to this group and returns "Eyelid" directly without needing a multi-class specialist.
> - Gradient accumulation (8 steps, effective batch = 32) and mixed precision (AMP) are used to fit within 6 GB VRAM.
> - `WeightedRandomSampler` with `TARGET_SAMPLES_PER_CLASS = 5000` balances classes each epoch.

---

### 4. Backend Setup

**Create a `.env` file** in the project root (see [Configuration](#configuration-env)).

**Start the FastAPI server:**

```bash
python backend/main.py
```

The API will be available at `http://localhost:8000`.  
Visit `http://localhost:8000/docs` for the interactive Swagger UI.

---

### 5. Frontend Setup

```bash
cd frontend
npm install
```

**Create a frontend environment file** (optional — defaults to `http://localhost:8000`):

```bash
VITE_API_URL=http://localhost:8000
```

**Start the development server:**

```bash
npm run dev
```

The app will open at `http://localhost:5173`.

**Build for production:**

```bash
npm run build
```

---

## Configuration (.env)

Create a `.env` file in the **project root** (next to `backend/`):

```env

ANTHROPIC_API_KEY=sk-ant-your-key-here

OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
```

**Priority:** If `ANTHROPIC_API_KEY` is set, Claude is used. If only `OLLAMA_URL` is set, Ollama is used. If neither is configured, the chat endpoint returns setup instructions.

**VRAM guidance for Ollama on RTX 3050 (6 GB):**

| Model | VRAM Required | Notes |
|-------|--------------|-------|
| `llama3.2:3b` | ~2.5 GB | ✅ Recommended — leaves headroom for vision models |
| `llama3.2:1b` | ~1 GB | ✅ Fastest option |
| `llava:7b` | ~5 GB | ⚠ Tight — disable inference GPU cache |
| `llama3.1:8b` | ~5.5 GB | ⚠ Very tight on 6 GB |

> By default, Ollama is configured with `"num_gpu": 0` in the backend, forcing CPU-only inference to avoid VRAM conflicts with the PyTorch vision models. Remove this setting if you have enough VRAM to run both.

---

## Running the Application

**Terminal 1 — Backend:**

```bash
python backend/main.py
```

**Terminal 2 — Frontend:**

```bash
cd frontend
npm run dev
```

**Terminal 3 — Ollama (if using local LLM):**

```bash
ollama serve
```

Open `http://localhost:5173` in your browser.

---

## API Reference

### `GET /`

Returns system status, device info, and active chat backend.

**Response:**
```json
{
  "status": "OphthalmoAI System Ready",
  "device": "cuda",
  "router_loaded": true,
  "specialists_loaded": 3,
  "chat_backend": "Anthropic Claude"
}
```

---

### `GET /health`

Simple health check.

**Response:**
```json
{ "ok": true, "device": "cuda" }
```

---

### `POST /predict`

Accepts an eye scan image and optional symptom data. Returns a full diagnostic result.

**Request** — `multipart/form-data`:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | `File` | ✅ | Eye scan image (JPG/PNG/BMP) |
| `pain` | `string` | ✅ | `"None"` / `"Mild"` / `"Severe"` / `"Not Sure"` |
| `vision` | `string` | ✅ | `"No"` / `"Yes"` / `"Not Sure"` |
| `itch` | `string` | ✅ | `"No"` / `"Yes"` / `"Not Sure"` |

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
  "details": {
    "description": "...",
    "analysis": "...",
    "symptoms": ["...", "..."],
    "treatment": ["...", "..."],
    "precautions": ["...", "..."],
    "severity": "Low (usually self-limiting, but contagious)",
    "advice": "..."
  }
}
```

---

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
  "diagnosis_context": { ... }
}
```

**Response:**
```json
{
  "reply": "Conjunctivitis (commonly called Pink Eye) is...",
  "model_used": "anthropic"
}
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Hierarchical Inference** | Two-stage pipeline: router → specialist, mirroring clinical triage |
| **Grad-CAM Heatmaps** | Visual attention maps showing which image regions drove the diagnosis |
| **Symptom Cross-Check** | Rule-based engine that validates AI diagnosis against reported symptoms |
| **Clinical Safety Alerts** | Flags dangerous diagnosis/symptom mismatches (e.g. severe pain in conjunctivitis) |
| **AI Doctor Chat** | Contextual ophthalmology Q&A powered by Claude or Ollama |
| **PDF Report Export** | 3-page clinical report with images, differential diagnosis, and treatment protocol |
| **Text-to-Speech** | Reads the diagnosis and clinical advice aloud via the Web Speech API |
| **Image Crop Tool** | Built-in crop interface to focus on the region of interest before analysis |
| **Find a Doctor** | One-click Google Maps link to find ophthalmologists nearby |

---

## Training Details

| Hyperparameter | Router | Specialists |
|---------------|--------|-------------|
| Architecture | MobileNetV3-Large | EfficientNet-B4 |
| Input size | 224 × 224 | 380 × 380 |
| Batch size | 32 | 4 (×8 accumulation = 32 effective) |
| Optimiser | Adam (lr=1e-3) | AdamW (lr=1e-4, wd=1e-4) |
| Scheduler | StepLR (step=7, γ=0.1) | CosineAnnealingLR |
| Epochs | 25 | 25 |
| Mixed Precision | ❌ | ✅ (AMP) |
| Augmentations | Rotation, RandomCrop, Flip, ColorJitter | Rotation, RandomCrop, Flip, ColorJitter |
| Class balancing | WeightedRandomSampler | WeightedRandomSampler |
| Virtual samples/epoch | 5000 × num_groups | 5000 × num_classes |

All models are fine-tuned from ImageNet pre-trained weights (`weights='DEFAULT'`).

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'torch'`**
→ Ensure your virtual environment is activated and PyTorch was installed with the CUDA wheel, not from `requirements.txt`.

**`Router model not found at models/router.pth`**
→ Run `python scripts/train_router.py` before starting the backend.

**CUDA out of memory during training**
→ Reduce `BATCH_SIZE` from 4 to 2 in the training scripts, or increase `ACCUMULATION_STEPS` to compensate.

**Chat endpoint returns setup instructions**
→ Neither `ANTHROPIC_API_KEY` nor `OLLAMA_URL` is set in `.env`. See [Configuration](#configuration-env).

**Ollama connection refused**
→ Ensure `ollama serve` is running in a separate terminal and the model has been pulled (`ollama pull llama3.2:3b`).

**Frontend can't reach the backend**
→ Check `VITE_API_URL` in `frontend/.env.local` and ensure CORS is not blocked. The backend allows all origins by default in development.

**Grad-CAM heatmap missing**
→ Grad-CAM requires `grad-cam>=1.5.4`. The Adnexal (Eyelid-only) group uses direct pass-through — no heatmap is generated for that group as no specialist model runs inference.

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgements

- [EfficientNet](https://arxiv.org/abs/1905.11946) — Tan & Le, Google Brain
- [Grad-CAM](https://arxiv.org/abs/1610.02391) — Selvaraju et al.
- [pytorch-grad-cam](https://github.com/jacobgil/pytorch-grad-cam) — Jacob Gildenblat
- [FastAPI](https://fastapi.tiangolo.com/) — Sebastián Ramírez
- [Anthropic Claude](https://www.anthropic.com/) — AI Doctor chat backend
