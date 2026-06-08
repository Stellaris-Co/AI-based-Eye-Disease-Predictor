import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader, WeightedRandomSampler
import numpy as np
import time
import sys
import copy
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, 'dataset')
MODEL_SAVE_PATH = os.path.join(PROJECT_ROOT, 'models', 'router.pth')
os.makedirs(os.path.dirname(MODEL_SAVE_PATH), exist_ok=True)
BATCH_SIZE = 32
IMG_SIZE = 224
EPOCHS = 25
LEARNING_RATE = 0.001
TARGET_SAMPLES_PER_GROUP = 5000

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"\n🚀 STARTING STAGE 1: ROUTER TRAINING")
    print(f"   🧠 Model:    MobileNetV3-Large")
    print(f"   ⚡ Hardware: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    if not os.path.exists(DATA_DIR):
        print(f"❌ Error: Dataset not found at {DATA_DIR}")
        return
    train_transforms = transforms.Compose([
        transforms.Resize((255, 255)),
        transforms.RandomRotation(15),
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.7, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])
    dataset = datasets.ImageFolder(DATA_DIR, transform=train_transforms)
    class_names = dataset.classes
    print(f"✅ Router Targets (Groups): {class_names}")
    targets = dataset.targets
    class_counts = np.bincount(targets)
    class_weights = 1. / class_counts
    sample_weights = [class_weights[t] for t in targets]
    num_samples = TARGET_SAMPLES_PER_GROUP * len(class_names)
    sampler = WeightedRandomSampler(
        weights=sample_weights,
        num_samples=num_samples,
        replacement=True
    )
    train_loader = DataLoader(dataset, batch_size=BATCH_SIZE, sampler=sampler, num_workers=0)
    print(f"⚖️  Sampler Active: Training on {num_samples} virtual images per epoch.")
    print("🏗️  Building MobileNetV3...")
    model = models.mobilenet_v3_large(weights='DEFAULT')
    num_ftrs = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(num_ftrs, len(class_names))
    model = model.to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.StepLR(optimizer, step_size=7, gamma=0.1)
    best_loss = float('inf')
    best_model_wts = copy.deepcopy(model.state_dict())
    print(f"--- Training for {EPOCHS} Epochs ---")
    for epoch in range(EPOCHS):
        model.train()
        running_loss = 0.0
        correct = 0
        total = 0
        for i, (inputs, labels) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()
            outputs = model(inputs)
            loss = criterion(outputs, labels)
            loss.backward()
            optimizer.step()
            running_loss += loss.item() * inputs.size(0)
            _, preds = torch.max(outputs, 1)
            correct += (preds == labels).sum().item()
            total += labels.size(0)
            if i % 20 == 0:
                sys.stdout.write(f"\rEpoch {epoch+1} | Batch {i}/{len(train_loader)} | Loss: {loss.item():.4f}")
                sys.stdout.flush()
        epoch_loss = running_loss / total
        epoch_acc = correct / total
        scheduler.step()
        print(f"\n   Done. Avg Loss: {epoch_loss:.4f} | Acc: {epoch_acc:.4f}")
        if epoch_loss < best_loss:
            best_loss = epoch_loss
            best_model_wts = copy.deepcopy(model.state_dict())
            torch.save(model.state_dict(), MODEL_SAVE_PATH)
            print("   ⭐ Best Router Saved!")
    print(f"\n✅ SUCCESS: Router Model Saved to {MODEL_SAVE_PATH}")
if __name__ == "__main__":
    main()
