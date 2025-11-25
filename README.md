# **OpthalmoAI – AI-Powered Eye Disease Detection**

[![Python Version](https://img.shields.io/badge/Python-3.10+-blue.svg)]()
[![Node Version](https://img.shields.io/badge/Node.js-18+-green.svg)]()
[![Stars](https://img.shields.io/github/stars/AkashKundu114/Eye-Disease-AI-Diagnosis.svg?style=social)]()
[![Forks](https://img.shields.io/github/forks/AkashKundu114/Eye-Disease-AI-Diagnosis.svg?style=social)]()
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)]()

---

## ⭐ **Overview**

**OpthalmoAI** is a **full-stack, AI-powered ophthalmology application** designed to detect **six major eye diseases** using a **state-of-the-art deep learning model (EfficientNetB3)**.  
It features a **responsive React frontend**, **secure FastAPI backend**, and an **optimized TensorFlow inference pipeline** for fast, real-time medical predictions.

---

## 🚀 **Key Features**

- **Deep Learning Model**: EfficientNetB3 trained on high-quality medical datasets  
- **FastAPI Backend**: Secure & efficient inference system  
- **React Frontend**: Clean UI with fast interactions  
- **Real-time Predictions**  
- **Cloud-ready architecture**  
- **Modular & scalable codebase**

---

## 🧠 **Model Architecture**

- Backbone: **EfficientNetB3**
- Input resolution: **300×300**
- Output: **6-class softmax**
- Exported format: **SavedModel / H5**

---

## 🖼️ Detection Categories

The system predicts the following:

1. **Cataract**  
2. **Glaucoma**  
3. **Diabetic Retinopathy**  
4. **AMD (Age-Related Macular Degeneration)**  
5. **Hypertensive Retinopathy**  
6. **Normal Healthy Eye**

---

## Frontend Setup
```bash
cd frontend
npm install
```

---

## ⚡ How to Run

### Step 1 — Dataset & Model
Download dataset → put in `dataset/` → train:
```bash
python scripts/train_model.py
```

Creates:
```
models/model.pth
```

### Step 2 — Start Backend
```bash
python backend/main.py
```

### Step 3 — Start Frontend
```bash
cd frontend
npm run dev
```

---

## 📂 Project Structure
```
backend/  
frontend/  
scripts/  
models/  
dataset/
```

---

## 📊 Architecture Diagram
```mermaid
flowchart TD

%% ============================================
%% FRONTEND SYSTEM
%% ============================================
subgraph FRONTEND React Vite Tailwind
    FE1[User Interface]
    FE2[Image Upload Module]
    FE3[Webcam Capture Module]
    FE4[Prediction Dashboard Results]

    FE1 --> FE2
    FE1 --> FE3
    FE2 --> API
    FE3 --> API
end

%% ============================================
%% API GATEWAY AND ROUTING
%% ============================================
API[FastAPI Main Router]
API --> VR[Validation and Request Parser]
VR --> BE

%% ============================================
%% BACKEND PROCESSING LAYERS
%% ============================================
subgraph BACKEND FastAPI Server
    BE[Application Controller]
    BP[Image Preprocessing Resize Normalize]
    BE --> BP
    BP --> MS
end

%% ============================================
%% MODEL SERVICE
%% ============================================
subgraph MODEL SERVICE PyTorch
    MS[Model Loader EfficientNetB3]
    MI[Inference Forward Pass]
    MP[Softmax Output Six Classes]
    MS --> MI --> MP
end

MP --> RESP

%% ============================================
%% RESPONSE HANDLING
%% ============================================
RESP[JSON Response Prediction Confidence]
RESP --> FE4

%% ============================================
%% TRAINING AND DATA PIPELINE
%% ============================================
subgraph TRAINING PIPELINE
    DS[Dataset Folder Eye Images]
    DA[Data Augmentation Flip Rotate Color Adjust]
    DL[Data Loader Train Validation Split]
    TM[Training Script train model py]
    EV[Model Evaluation Metrics]
    SM[Save Model File models model pth]

    DS --> DA --> DL --> TM --> EV --> SM
end

%% BACKEND LOADS TRAINED MODEL
SM --> MS

%% ============================================
%% STORAGE SYSTEM
%% ============================================
subgraph STORAGE
    ST1[Model Files model pth]
    ST2[Dataset Local or External]
    ST3[Training Logs and Metrics]
end

SM --> ST1
DS --> ST2
EV --> ST3
```

