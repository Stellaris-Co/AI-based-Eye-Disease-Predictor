"""
Calibrate confidence scores for OphthalmoAI's specialist models.

Run once after training, before production deployment:
    python scripts/calibrate_models.py

Reads your dataset split from dataset/ (or a --val-dir override), runs each
trained specialist model's validation set through the TemperatureScaler, and
writes models/calibration.json with the optimal temperature per group.

After calibration, the /predict endpoint's confidence figures will actually reflect
the model's measured accuracy rather than being systematically overconfident.
"""
import argparse
import json
import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import torch
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms
import torch.nn as nn

from backend.calibration import CalibrationRegistry, TemperatureScaler

MODELS_DIR = os.path.join(project_root, "models")
CALIBRATION_PATH = os.path.join(MODELS_DIR, "calibration.json")

SPECIALISTS = {
    "anterior": {
        "model_file": "specialist_anterior.pth",
        "dataset_dir": "Anterior Segment Pathology",
        "num_classes": 2,
    },
    "surface": {
        "model_file": "specialist_surface.pth",
        "dataset_dir": "Ocular Surface Disorders",
        "num_classes": 4,
    },
}

VAL_TRANSFORMS = transforms.Compose([
    transforms.Resize((380, 380)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
])


def build_efficientnet(num_classes: int) -> nn.Module:
    model = models.efficientnet_b4(weights=None)
    model.classifier[1] = nn.Linear(model.classifier[1].in_features, num_classes)
    return model


def calibrate_one(
    group_key: str,
    model_path: str,
    val_dir: str,
    num_classes: int,
    device: torch.device,
) -> float:
    print(f"\n── Calibrating {group_key} ──")
    if not os.path.exists(model_path):
        print(f"  SKIP: {model_path} not found")
        return 1.0
    if not os.path.isdir(val_dir):
        print(f"  SKIP: validation dir {val_dir} not found")
        return 1.0

    dataset = datasets.ImageFolder(val_dir, transform=VAL_TRANSFORMS)
    loader = DataLoader(dataset, batch_size=16, shuffle=False, num_workers=0)
    print(f"  Validation set: {len(dataset)} images, {len(dataset.classes)} classes")

    model = build_efficientnet(num_classes)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.to(device).eval()

    scaler = TemperatureScaler(model)
    temperature = scaler.fit(loader, device)
    print(f"  Optimal temperature: {temperature:.4f}")
    return temperature


def main():
    parser = argparse.ArgumentParser(description="Calibrate OphthalmoAI specialist models")
    parser.add_argument("--data-dir", default=os.path.join(project_root, "dataset"),
                        help="Root dataset directory")
    parser.add_argument("--models-dir", default=MODELS_DIR,
                        help="Directory containing .pth files")
    parser.add_argument("--device", default="auto",
                        help="'auto', 'cpu', or 'cuda'")
    args = parser.parse_args()

    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)
    print(f"Using device: {device}")

    temperatures = {}
    for group_key, cfg in SPECIALISTS.items():
        model_path = os.path.join(args.models_dir, cfg["model_file"])
        val_dir = os.path.join(args.data_dir, cfg["dataset_dir"])
        t = calibrate_one(group_key, model_path, val_dir, cfg["num_classes"], device)
        temperatures[group_key] = round(t, 6)

    os.makedirs(args.models_dir, exist_ok=True)
    CalibrationRegistry.save(CALIBRATION_PATH, temperatures)
    print(f"\n✅ Calibration saved to {CALIBRATION_PATH}")
    print(json.dumps(temperatures, indent=2))


if __name__ == "__main__":
    main()
