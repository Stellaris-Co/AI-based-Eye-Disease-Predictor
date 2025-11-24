import streamlit as st
import torch
import torch.nn as nn
from torchvision import models, transforms
from PIL import Image, ImageOps
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL_PATH = os.path.join(PROJECT_ROOT, 'model.pth')

CLASSES = ['Cataract', 'Conjunctivitis', 'Eyelid', 'Jaundice', 'Normal', 'Uveitis']

MEDICAL_INFO = {
    'Cataract': {'description': "Clouding of the eye lens.", 'symptoms': ["Blurry vision"], 'treatment': ["Surgery"], 'action': "See ophthalmologist."},
    'Conjunctivitis': {'description': "Pink Eye.", 'symptoms': ["Redness", "Itch"], 'treatment': ["Drops"], 'action': "Isolate & Hygiene."},
    'Eyelid': {'description': "Inflammation (Stye/Blepharitis).", 'symptoms': ["Swelling"], 'treatment': ["Warm compress"], 'action': "Home care."},
    'Jaundice': {'description': "Yellowing of eyes.", 'symptoms': ["Yellow skin"], 'treatment': ["Treat liver"], 'action': "URGENT Medical Care."},
    'Uveitis': {'description': "Inflammation of uvea.", 'symptoms': ["Pain", "Light sensitivity"], 'treatment': ["Steroids"], 'action': "URGENT Eye Doctor."},
    'Normal': {'description': "Healthy.", 'symptoms': [], 'treatment': [], 'action': "Routine checkup."}
}

st.set_page_config(page_title="Eye AI Diagnostics", page_icon="👁️")

@st.cache_resource
def load_model():
    if not os.path.exists(MODEL_PATH): return None
    try:
        model = models.efficientnet_b3(weights=None)
        model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(CLASSES))
        model.load_state_dict(torch.load(MODEL_PATH, map_location='cpu'))
        model.eval()
        return model
    except: return None

def main():
    st.title("👁️ Eye Disease AI")
    model = load_model()
    
    if model is None:
        st.error(f"Model not found at {MODEL_PATH}. Train first!")
        return

    uploaded_file = st.file_uploader("Upload Scan", type=["jpg", "png"])
    
    if uploaded_file:
        image = Image.open(uploaded_file).convert('RGB')
        st.image(image, caption='Scan', width=300)
        
        if st.button("Analyze"):
            preprocess = transforms.Compose([
                transforms.Resize((224, 224)), transforms.ToTensor(),
                transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
            ])
            input_tensor = preprocess(image).unsqueeze(0)
            
            with torch.no_grad():
                output = model(input_tensor)
                probs = torch.nn.functional.softmax(output[0], dim=0)
            
            conf, idx = torch.max(probs, 0)
            cls = CLASSES[idx.item()]
            
            st.subheader(f"Result: {cls} ({conf.item()*100:.1f}%)")
            info = MEDICAL_INFO.get(cls, {})
            st.info(f"**Action:** {info.get('action', '')}")

if __name__ == "__main__":
    main()