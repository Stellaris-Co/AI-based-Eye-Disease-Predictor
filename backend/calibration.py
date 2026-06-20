"""
Confidence calibration for OphthalmoAI's specialist models.

Deep neural networks are systematically overconfident: a model reporting "94.7%
Conjunctivitis" is very often wrong far more than 5.3% of the time. Temperature
scaling (Guo et al., 2017, https://arxiv.org/abs/1706.04599) fixes this with a single
learned scalar T per model, applied as logits / T before softmax. T > 1 makes the
model less confident (the usual direction); T < 1 would make it more confident.

This module provides:
  - TemperatureScaler: wraps a trained model and learns T against a validation set
  - CalibrationRegistry: loads/saves per-group temperatures from models/calibration.json
  - apply_temperature(): the actual logits/T operation used at inference time in main.py

If no calibration.json is present (e.g. a fresh clone with no calibration run yet),
every temperature defaults to 1.0 — i.e. behaves exactly like the uncalibrated model,
so this is always safe to import even before anyone runs scripts/calibrate_models.py.
"""
from __future__ import annotations

import json
import os
from typing import Dict, Optional

import torch
import torch.nn as nn


DEFAULT_TEMPERATURE = 1.0


class TemperatureScaler(nn.Module):

    def __init__(self, model: nn.Module):
        super().__init__()
        self.model = model
        self.temperature = nn.Parameter(torch.ones(1) * 1.5)

    def forward(self, x):
        return self.model(x) / self.temperature

    def fit(self, val_loader, device, max_iter: int = 50, lr: float = 0.01) -> float:
        self.model.eval()
        nll_criterion = nn.CrossEntropyLoss()
        optimizer = torch.optim.LBFGS([self.temperature], lr=lr, max_iter=max_iter)

        logits_list, labels_list = [], []
        with torch.no_grad():
            for inputs, labels in val_loader:
                logits_list.append(self.model(inputs.to(device)))
                labels_list.append(labels.to(device))
        logits = torch.cat(logits_list)
        labels = torch.cat(labels_list)

        def closure():
            optimizer.zero_grad()
            loss = nll_criterion(logits / self.temperature, labels)
            loss.backward()
            return loss

        optimizer.step(closure)
        return float(self.temperature.item())


def apply_temperature(logits: torch.Tensor, temperature: float) -> torch.Tensor:
    if temperature is None or temperature <= 0:
        temperature = DEFAULT_TEMPERATURE
    return logits / temperature


class CalibrationRegistry:

    def __init__(self, path: str):
        self.path = path
        self._temperatures: Dict[str, float] = {}
        self.loaded_at: Optional[str] = None
        self.reload()

    def reload(self) -> None:
        if os.path.exists(self.path):
            try:
                with open(self.path, "r") as f:
                    data = json.load(f)
                self._temperatures = {k: float(v) for k, v in data.items()}
            except Exception as e:
                print(f"⚠️  Failed to load calibration file at {self.path}: {e}")
                self._temperatures = {}
        else:
            self._temperatures = {}

    def get(self, group_key: str) -> float:
        return self._temperatures.get(group_key, DEFAULT_TEMPERATURE)

    def is_calibrated(self, group_key: str) -> bool:
        return group_key in self._temperatures

    def all(self) -> Dict[str, float]:
        return dict(self._temperatures)

    @staticmethod
    def save(path: str, temperatures: Dict[str, float]) -> None:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w") as f:
            json.dump(temperatures, f, indent=2)
