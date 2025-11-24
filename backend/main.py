from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
import torch
from torchvision import models, transforms
from PIL import Image
import io
import uvicorn
import torch.nn as nn
import os
import sys

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
MODEL_PATH = os.path.join(project_root, "model.pth")

CLASSES = ['Cataract', 'Conjunctivitis', 'Eyelid', 'Jaundice', 'Normal', 'Uveitis']
DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

MEDICAL_INFO = {
    'Cataract': {
        'description': "Clouding of the eye's natural lens.",
        'symptoms': ["Blurry vision", "Faded colors", "Poor night vision", "Halos around lights"],
        'treatment': ["Prescription glasses", "Cataract Surgery (Phacoemulsification)"],
        'severity': "Moderate"
    },
    'Conjunctivitis': {
        'description': "Inflammation of the conjunctiva (Pink Eye).",
        'symptoms': ["Redness", "Itchiness", "Gritty feeling", "Discharge"],
        'treatment': ["Artificial tears", "Antibiotic drops", "Cold compresses"],
        'severity': "Low (usually)"
    },
    'Eyelid': {
        'description': "Inflammation of the eyelid margin (Blepharitis/Stye).",
        'symptoms': ["Swollen eyelids", "Crusty debris", "Redness"],
        'treatment': ["Warm compresses", "Eyelid scrubs", "Antibiotic ointment"],
        'severity': "Low"
    },
    'Jaundice': {
        'description': "Yellowing of the white part of the eye (Sclera).",
        'symptoms': ["Yellow eyes/skin", "Dark urine", "Fatigue"],
        'treatment': ["Treat underlying liver/gallbladder issue", "Urgent medical care"],
        'severity': "High (Systemic Issue)"
    },
    'Uveitis': {
        'description': "Inflammation of the middle layer of the eye.",
        'symptoms': ["Deep eye pain", "Light sensitivity", "Blurred vision"],
        'treatment': ["Steroid drops", "Dilating drops", "Immunosuppressants"],
        'severity': "High (Risk of vision loss)"
    },
    'Normal': {
        'description': "Healthy eye presentation.",
        'symptoms': ["None"],
        'treatment': ["Routine eye exams"],
        'severity': "None"
    }
}

def load_model():
    print(f"Looking for model at: {MODEL_PATH}")
    if not os.path.exists(MODEL_PATH):
        print(f"❌ Error: Model file not found at {MODEL_PATH}")
        return None

    print("Loading model architecture...")
    model = models.efficientnet_b3(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(CLASSES))
    
    try:
        state_dict = torch.load(MODEL_PATH, map_location=DEVICE)
        model.load_state_dict(state_dict)
        model.to(DEVICE)
        model.eval()
        print("✅ Model loaded successfully!")
        return model
    except Exception as e:
        print(f"❌ Failed to load model weights: {e}")
        return None

model = load_model()

preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
])

@app.post("/predict")
async def predict(file: UploadFile = File(...)):
    if model is None:
        return {"error": "Model not loaded"}

    try:
        contents = await file.read()
        image = Image.open(io.BytesIO(contents)).convert('RGB')
        
        input_tensor = preprocess(image).unsqueeze(0).to(DEVICE)

        with torch.no_grad():
            output = model(input_tensor)
            probs = torch.nn.functional.softmax(output[0], dim=0)
            
        confidence, index = torch.max(probs, 0)
        class_name = CLASSES[index.item()]
        
        return {
            "diagnosis": class_name,
            "confidence": float(confidence.item()) * 100,
            "details": MEDICAL_INFO.get(class_name, {}),
            "probabilities": {CLASSES[i]: float(probs[i].item()) for i in range(len(CLASSES))}
        }
    except Exception as e:
        print(f"Prediction Error: {e}")
        return {"error": str(e)}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
