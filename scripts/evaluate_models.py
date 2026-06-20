"""
Evaluate OphthalmoAI specialist models on held-out validation data.

Run after training (and optionally after calibration):
    python scripts/evaluate_models.py

Produces:
  - Console table of sensitivity / specificity / AUC / ECE per class
  - models/validation_report.json with machine-readable metrics

The JSON report is what you reference in docs/CLINICAL_VALIDATION.md and what
register_model() in backend/model_registry.py stores alongside each checkpoint.
"""
import argparse
import json
import os
import sys
from datetime import datetime, timezone

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

try:
    from sklearn.metrics import roc_auc_score, confusion_matrix, classification_report
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from backend.calibration import CalibrationRegistry, apply_temperature

MODELS_DIR = os.path.join(project_root, "models")
CALIBRATION_PATH = os.path.join(MODELS_DIR, "calibration.json")
REPORT_PATH = os.path.join(MODELS_DIR, "validation_report.json")

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


def expected_calibration_error(probs: np.ndarray, labels: np.ndarray, n_bins: int = 10) -> float:
    """Computes ECE: mean |accuracy - confidence| across probability bins.
    Lower is better (0.0 = perfectly calibrated)."""
    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0
    confidences = probs.max(axis=1)
    predictions = probs.argmax(axis=1)
    correct = (predictions == labels).astype(float)
    for i in range(n_bins):
        lo, hi = bin_boundaries[i], bin_boundaries[i + 1]
        in_bin = (confidences >= lo) & (confidences < hi)
        if in_bin.sum() == 0:
            continue
        acc = correct[in_bin].mean()
        conf = confidences[in_bin].mean()
        ece += abs(acc - conf) * in_bin.sum() / len(labels)
    return float(ece)


def evaluate_one(
    group_key: str,
    model_path: str,
    val_dir: str,
    num_classes: int,
    device: torch.device,
    temperature: float,
) -> dict:
    print(f"\n── Evaluating {group_key} (T={temperature:.4f}) ──")
    if not os.path.exists(model_path):
        print(f"  SKIP: {model_path} not found")
        return {}
    if not os.path.isdir(val_dir):
        print(f"  SKIP: val dir {val_dir} not found")
        return {}

    dataset = datasets.ImageFolder(val_dir, transform=VAL_TRANSFORMS)
    loader = DataLoader(dataset, batch_size=16, shuffle=False, num_workers=0)
    class_names = dataset.classes
    print(f"  {len(dataset)} images, classes: {class_names}")

    model = build_efficientnet(num_classes)
    model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
    model.to(device).eval()

    all_logits, all_labels = [], []
    with torch.no_grad():
        for inputs, labels in loader:
            logits = model(inputs.to(device))
            all_logits.append(logits.cpu())
            all_labels.append(labels)

    logits_t = torch.cat(all_logits)
    labels_np = torch.cat(all_labels).numpy()
    probs_np = F.softmax(apply_temperature(logits_t, temperature), dim=1).numpy()
    preds_np = probs_np.argmax(axis=1)

    accuracy = float((preds_np == labels_np).mean())
    ece = expected_calibration_error(probs_np, labels_np)
    print(f"  Accuracy: {accuracy:.4f}  ECE: {ece:.4f}")

    per_class = {}
    if SKLEARN_AVAILABLE:
        cm = confusion_matrix(labels_np, preds_np)
        for i, cls in enumerate(class_names):
            tp = cm[i, i]
            fn = cm[i, :].sum() - tp
            fp = cm[:, i].sum() - tp
            tn = cm.sum() - tp - fn - fp
            sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
            try:
                binary_labels = (labels_np == i).astype(int)
                auc = float(roc_auc_score(binary_labels, probs_np[:, i]))
            except Exception:
                auc = None
            per_class[cls] = {
                "sensitivity": round(sensitivity, 4),
                "specificity": round(specificity, 4),
                "auc": round(auc, 4) if auc is not None else None,
                "n_samples": int((labels_np == i).sum()),
            }
            auc_str = f"{auc:.3f}" if auc else "N/A"
            print(f"  {cls:20s}  sens={sensitivity:.3f}  spec={specificity:.3f}"
                  f"  AUC={auc_str}")

    return {
        "group_key": group_key,
        "model_file": os.path.basename(model_path),
        "num_classes": num_classes,
        "class_names": class_names,
        "n_total": len(dataset),
        "accuracy": round(accuracy, 4),
        "ece": round(ece, 4),
        "calibration_temperature": temperature,
        "per_class": per_class,
        "evaluated_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    parser = argparse.ArgumentParser(description="Evaluate OphthalmoAI specialist models")
    parser.add_argument("--data-dir", default=os.path.join(project_root, "dataset"))
    parser.add_argument("--models-dir", default=MODELS_DIR)
    parser.add_argument("--device", default="auto")
    args = parser.parse_args()

    if not SKLEARN_AVAILABLE:
        print("⚠️  scikit-learn not installed — skipping per-class AUC/sensitivity/specificity")

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    ) if args.device == "auto" else torch.device(args.device)
    print(f"Device: {device}")

    registry = CalibrationRegistry(CALIBRATION_PATH)

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "models_dir": args.models_dir,
        "results": {},
    }
    for group_key, cfg in SPECIALISTS.items():
        result = evaluate_one(
            group_key=group_key,
            model_path=os.path.join(args.models_dir, cfg["model_file"]),
            val_dir=os.path.join(args.data_dir, cfg["dataset_dir"]),
            num_classes=cfg["num_classes"],
            device=device,
            temperature=registry.get(group_key),
        )
        if result:
            report["results"][group_key] = result

    with open(REPORT_PATH, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\n✅ Validation report saved to {REPORT_PATH}")


if __name__ == "__main__":
    main()
