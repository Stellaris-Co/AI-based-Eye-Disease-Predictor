👁️ OphthalmoAI - Eye Disease Diagnostic System

A full-stack AI application for detecting 6 types of eye diseases using Deep Learning (EfficientNetB3).

🚀 Features

High Accuracy AI: Trained on 2,500+ medical images (Cataract, Uveitis, Conjunctivitis, etc.).

Live Webcam Mode: Real-time inference using OpenCV.

Medical Dashboard: Professional interface built with React & Tailwind CSS.

FastAPI Backend: High-performance Python API for inference.

🛠️ Installation

1. Clone the Repo

git clone [https://github.com/YOUR_USERNAME/Eye-Disease-AI-Diagnosis.git](https://github.com/YOUR_USERNAME/Eye-Disease-AI-Diagnosis.git)
cd Eye-Disease-AI-Diagnosis


2. Backend Setup (The Brain)

python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt


3. Frontend Setup (The UI)

cd frontend
npm install


⚡ How to Run

Step 1: Get the Data & Model

Note: The dataset and model are not included in this repo due to size limits.

Download your dataset and place it in a folder named dataset/ in the root.

Train the model to generate the brain:

python scripts/train_model.py


This will create models/model.pth.

Step 2: Start the Backend

# From root directory
python backend/main.py


Step 3: Start the Frontend

# New terminal
cd frontend
npm run dev


📂 Project Structure

backend/ - FastAPI server & inference logic.

frontend/ - React + Vite + Tailwind dashboard.

scripts/ - Utilities for training, testing, and data cleaning.

models/ - Stores the trained .pth file (Local only).