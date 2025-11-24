import os
import torch
import torch.nn as nn
import torch.optim as optim
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
import numpy as np
import copy
import time
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)

DATA_DIR = os.path.join(project_root, 'dataset')
MODEL_PATH = os.path.join(project_root, 'model.pth')

BATCH_SIZE = 16   
IMG_SIZE = 224
EPOCHS = 30       
LEARNING_RATE = 0.001
SEED = 123 

def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 Training on: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU'}")
    print(f"📂 Saving model to: {MODEL_PATH}")
    
    torch.manual_seed(SEED)

    train_transforms = transforms.Compose([
        transforms.Resize((255, 255)),
        transforms.RandomRotation(20),
        transforms.RandomResizedCrop(IMG_SIZE, scale=(0.8, 1.0)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.15, contrast=0.15),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
    ])

    if not os.path.exists(DATA_DIR):
        print(f"❌ Error: Dataset not found at {DATA_DIR}")
        return

    full_dataset = datasets.ImageFolder(DATA_DIR, transform=train_transforms)
    class_names = full_dataset.classes
    print(f"✅ Classes: {class_names}")

    targets = full_dataset.targets
    class_counts = np.bincount(targets)
    total_samples = len(full_dataset)
    class_weights = total_samples / (len(class_names) * class_counts)
    class_weights_tensor = torch.FloatTensor(class_weights).to(device)
    
    print("--- Class Weights ---")
    for i, c in enumerate(class_names):
        print(f"• {c}: {class_weights[i]:.2f}")

    train_loader = DataLoader(full_dataset, batch_size=BATCH_SIZE, shuffle=True, num_workers=0)
    total_batches = len(train_loader)

    print("\nBuilding EfficientNetB3...")
    model = models.efficientnet_b3(weights='DEFAULT')
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, len(class_names))
    model = model.to(device)

    criterion = nn.CrossEntropyLoss(weight=class_weights_tensor)
    optimizer = optim.Adam(model.parameters(), lr=LEARNING_RATE)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.1, patience=3)

    best_loss = float('inf')
    best_model_wts = copy.deepcopy(model.state_dict())

    print("--- Starting Training ---")
    start_time = time.time()

    for epoch in range(EPOCHS):
        print(f'\nEpoch {epoch+1}/{EPOCHS}')
        print("-" * 20)
        
        model.train() 
        running_loss = 0.0
        running_corrects = 0

        for i, (inputs, labels) in enumerate(train_loader):
            inputs, labels = inputs.to(device), labels.to(device)
            optimizer.zero_grad()

            outputs = model(inputs)
            _, preds = torch.max(outputs, 1)
            loss = criterion(outputs, labels)

            loss.backward()
            optimizer.step()

            running_loss += loss.item() * inputs.size(0)
            running_corrects += torch.sum(preds == labels.data)

            if (i + 1) % 5 == 0:
                sys.stdout.write(f"\r   > Batch {i+1}/{total_batches} | Loss: {loss.item():.4f}")
                sys.stdout.flush()

        epoch_loss = running_loss / len(full_dataset)
        epoch_acc = running_corrects.double() / len(full_dataset)

        print(f"\n   RESULT: Loss: {epoch_loss:.4f} | Acc: {epoch_acc:.4f}")

        if epoch_loss < best_loss:
            best_loss = epoch_loss
            best_model_wts = copy.deepcopy(model.state_dict())
            print(f"   ⭐ New Best Model! Saving checkpoint.")
        
        scheduler.step(epoch_loss)

    time_elapsed = time.time() - start_time
    print(f'\nTraining complete in {time_elapsed // 60:.0f}m {time_elapsed % 60:.0f}s')

    model.load_state_dict(best_model_wts)
    torch.save(model.state_dict(), MODEL_PATH)
    print(f"✅ Final Model saved to {MODEL_PATH}")

if __name__ == "__main__":
    main()