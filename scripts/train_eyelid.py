import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader, WeightedRandomSampler, Dataset
from torch.cuda.amp import GradScaler, autocast
from PIL import Image
import numpy as np
import sys
import time
import warnings
from tqdm import tqdm
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)
os.environ['KMP_DUPLICATE_LIB_OK']='True'
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TARGET_FOLDER = 'Adnexal Oculoplastic'
MODEL_SAVE_PATH = os.path.join(PROJECT_ROOT, 'models', 'specialist_eyelid.pth')
DATA_DIR = os.path.join(PROJECT_ROOT, 'dataset', TARGET_FOLDER)
os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
BATCH_SIZE = 4
ACCUMULATION_STEPS = 8
IMG_SIZE = 380
EPOCHS = 25
LEARNING_RATE = 1e-4
TARGET_SAMPLES_PER_CLASS = 5000

class SpecialistDataset(Dataset):
    def __init__(self, root_dir, transform=None):
        self.root_dir = root_dir
        self.transform = transform
        self.samples = []
        self.classes = sorted([d for d in os.listdir(root_dir) if os.path.isdir(os.path.join(root_dir, d))])
        self.class_to_idx = {cls_name: i for i, cls_name in enumerate(self.classes)}
        for disease in self.classes:
            disease_path = os.path.join(root_dir, disease)
            for img in os.listdir(disease_path):
                if img.lower().endswith(('.png', '.jpg', '.jpeg', '.bmp')):
                    self.samples.append((os.path.join(disease_path, img), disease))
        self.targets = [self.class_to_idx[s[1]] for s in self.samples]
        if not self.classes: sys.exit("Error: No classes found in target folder.")
    def __len__(self): return len(self.samples)
    def __getitem__(self, idx):
        path, label_str = self.samples[idx]
        image = Image.open(path).convert('RGB')
        if self.transform: image = self.transform(image)
        label = self.class_to_idx[label_str]
        return image, label

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n🚀 STAGE 2: EYELID SPECIALIST TRAINING ({TARGET_FOLDER})")
    print(f"   ⚡ Hardware: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    train_transforms = transforms.Compose([
        transforms.Resize((400, 400)),
        transforms.RandomRotation(25),
        transforms.RandomCrop(IMG_SIZE),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    dataset = SpecialistDataset(DATA_DIR, transform=train_transforms)
    num_classes = len(dataset.classes)
    total_virtual_samples = TARGET_SAMPLES_PER_CLASS * num_classes
    sampler = WeightedRandomSampler(weights=[1.0]*len(dataset), num_samples=total_virtual_samples, replacement=True)
    train_loader = DataLoader(dataset, batch_size=BATCH_SIZE, sampler=sampler, num_workers=0, pin_memory=True)
    print(f"⚖️  Training on {total_virtual_samples} virtual samples per epoch.")
    print(f"⚠️  NOTE: Since 1 class, using MSELoss for placeholder stability.")
    model = models.efficientnet_b4(weights='DEFAULT')
    for param in model.parameters(): param.requires_grad = True
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, 1)
    model = model.to(device)
    criterion = nn.MSELoss()
    optimizer = optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=1e-4)
    scaler = GradScaler()
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=EPOCHS)
    best_loss = float('inf')
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        pbar = tqdm(train_loader, desc=f"Adnexal Epoch {epoch+1}/{EPOCHS}")
        for i, (inputs, labels) in enumerate(pbar):
            inputs = inputs.to(device)
            labels_float = labels.float().unsqueeze(1).to(device)
            optimizer.zero_grad()
            with autocast():
                outputs = model(inputs)
                loss = criterion(outputs, labels_float)
                loss = loss / ACCUMULATION_STEPS
            scaler.scale(loss).backward()
            if (i + 1) % ACCUMULATION_STEPS == 0:
                scaler.step(optimizer)
                scaler.update()
                optimizer.zero_grad()
            running_loss += loss.item() * ACCUMULATION_STEPS * inputs.size(0)
            pbar.set_postfix({'Loss': f'{loss.item()*ACCUMULATION_STEPS:.4f}'})
        epoch_loss = running_loss / total_virtual_samples
        scheduler.step()
        print(f"\n[Epoch {epoch+1} Results] | Avg Loss: {epoch_loss:.4f}")
        if epoch_loss < best_loss:
            best_loss = epoch_loss
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print("   ⭐ Best Model Saved!")
if __name__ == "__main__":
    try:
        from tqdm import tqdm
    except ImportError:
        print("Install tqdm: pip install tqdm")
        sys.exit(1)
    main()
