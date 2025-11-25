# 👁️ OphthalmoAI – Eye Disease Diagnostic System

A full-stack, **AI-powered ophthalmology application** designed to detect **six major eye diseases** using a state-of-the-art deep learning model based on **EfficientNetB3**. The system integrates **a responsive React frontend**, **a secure FastAPI backend**, and **an optimized TensorFlow inference pipeline** to deliver **fast**, **accurate**, **real-world medical predictions**.

---

## 🚀 Features

### 🧠 AI Model  
- Trained on **3,500+ medical eye images**  
- Detects: Cataract, Uveitis, Conjunctivitis, and more  
- High accuracy with EfficientNetB3 architecture  

### 📸 Real-time Webcam Mode  
- Live inference using OpenCV  

### 🏥 Medical Dashboard  
- React + Tailwind CSS interface  

### ⚡ FastAPI Backend  
- High-performance inference  

---

## 🛠️ Installation Guide

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/Eye-Disease-AI-Diagnosis.git
cd Eye-Disease-AI-Diagnosis
```

---

## Backend Setup
```bash
python -m venv venv
venv\Scripts\activate   # Windows
source venv/bin/activate # Mac/Linux
pip install -r requirements.txt
```

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

