"""
Tests for all new clinical-grade backend modules.

Run with:
    pytest tests/backend/ -v

These tests are intentionally self-contained — no GPU, no model weights, no external
services needed. Mocks are used for anything that touches the DB or file system.
"""
import os
import sys
import json
import tempfile
import unittest
from io import BytesIO
from typing import List
from unittest.mock import MagicMock, patch

import numpy as np
import torch
import torch.nn as nn

project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from PIL import Image


class TestAnalyzeSymptoms(unittest.TestCase):
    """Every rule in _build_symptom_alerts() must fire exactly when expected."""

    def _run(self, **kwargs):
        from backend.main import analyze_symptoms, analyze_symptoms_structured
        defaults = dict(
            diagnosis="Normal", pain_level="None", vision_loss="No",
            itchiness="No", halos="No", discharge="None",
            light_sensitivity="No", floaters="No", duration="Not Sure",
        )
        defaults.update(kwargs)
        legacy = analyze_symptoms(**defaults)
        structured = analyze_symptoms_structured(**defaults)
        return legacy, structured

    def test_conjunctivitis_severe_pain_fires(self):
        legacy, structured = self._run(diagnosis="Conjunctivitis", pain_level="Severe")
        self.assertTrue(any("Pain Mismatch" in w for w in legacy))
        self.assertTrue(any(e["severity"] == "warning" for e in structured))

    def test_conjunctivitis_itch_match(self):
        legacy, _ = self._run(diagnosis="Conjunctivitis", itchiness="Yes")
        self.assertTrue(any("Itchiness" in w for w in legacy))

    def test_jaundice_always_urgent(self):
        legacy, structured = self._run(diagnosis="Jaundice")
        self.assertTrue(any("🚨" in w for w in legacy))
        self.assertTrue(any(e["severity"] == "urgent" for e in structured))

    def test_uveitis_pain_urgent(self):
        legacy, structured = self._run(diagnosis="Uveitis", pain_level="Severe")
        self.assertTrue(any("sight-threatening" in w for w in legacy))
        self.assertTrue(any(e["severity"] == "urgent" for e in structured))

    def test_cataract_halos_match(self):
        legacy, _ = self._run(diagnosis="Cataract", halos="Yes")
        self.assertTrue(any("Halos" in w for w in legacy))

    def test_floaters_not_uveitis_fires(self):
        legacy, _ = self._run(diagnosis="Conjunctivitis", floaters="Yes")
        self.assertTrue(any("Floaters" in w for w in legacy))

    def test_floaters_uveitis_no_extra_warning(self):
        legacy, _ = self._run(diagnosis="Uveitis", floaters="Yes")
        self.assertFalse(any("Floaters" in w for w in legacy))

    def test_uveitis_light_sensitivity_urgent(self):
        legacy, structured = self._run(diagnosis="Uveitis", light_sensitivity="Yes")
        self.assertTrue(any("Light sensitivity" in w for w in legacy))
        self.assertTrue(any(e["severity"] == "urgent" for e in structured))

    def test_conjunctivitis_purulent_discharge_info(self):
        legacy, structured = self._run(diagnosis="Conjunctivitis", discharge="Thick/Yellow")
        self.assertTrue(any("discharge" in w.lower() for w in legacy))
        self.assertTrue(any(e["severity"] == "info" for e in structured))

    def test_chronic_duration_conjunctivitis_warning(self):
        legacy, structured = self._run(diagnosis="Conjunctivitis", duration=">1 month")
        self.assertTrue(any("Chronic" in w for w in legacy))
        self.assertTrue(any(e["severity"] == "warning" for e in structured))

    def test_normal_no_alerts(self):
        legacy, structured = self._run(diagnosis="Normal")
        self.assertEqual(legacy, [])
        self.assertEqual(structured, [])

    def test_structured_shape(self):
        _, structured = self._run(diagnosis="Jaundice")
        for entry in structured:
            self.assertIn("severity", entry)
            self.assertIn("message", entry)
            self.assertIn(entry["severity"], ("info", "warning", "urgent"))
            self.assertIsInstance(entry["message"], str)
            self.assertGreater(len(entry["message"]), 0)


class TestIQA(unittest.TestCase):

    def _make_image(self, brightness: int = 128, blur: bool = False, size=(380, 380)):
        arr = np.full((*size, 3), brightness, dtype=np.uint8)
        img = Image.fromarray(arr, mode="RGB")
        return img

    def test_bright_uniform_image_is_dark(self):
        from backend.iqa import assess_image_quality
        dark = self._make_image(brightness=10)
        acceptable, issues = assess_image_quality(dark)
        self.assertFalse(acceptable)
        self.assertTrue(any("dark" in i.lower() for i in issues))

    def test_overexposed_image_warned(self):
        from backend.iqa import assess_image_quality
        bright = self._make_image(brightness=240)
        acceptable, issues = assess_image_quality(bright)
        self.assertFalse(acceptable)
        self.assertTrue(any("overexposed" in i.lower() for i in issues))

    def test_normal_brightness_acceptable(self):
        from backend.iqa import assess_image_quality, CV2_AVAILABLE
        normal = self._make_image(brightness=128)
        acceptable, issues = assess_image_quality(normal)
        brightness_issues = [i for i in issues if "dark" in i.lower() or "overexposed" in i.lower()]
        self.assertEqual(brightness_issues, [])

    def test_returns_tuple(self):
        from backend.iqa import assess_image_quality
        img = self._make_image()
        result = assess_image_quality(img)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], bool)
        self.assertIsInstance(result[1], list)


class TestCalibration(unittest.TestCase):

    def test_apply_temperature_identity(self):
        from backend.calibration import apply_temperature
        logits = torch.tensor([1.0, 2.0, 3.0])
        result = apply_temperature(logits, 1.0)
        self.assertTrue(torch.allclose(result, logits))

    def test_apply_temperature_softens(self):
        from backend.calibration import apply_temperature
        import torch.nn.functional as F
        logits = torch.tensor([1.0, 2.0, 3.0])
        probs_uncal = F.softmax(logits, dim=0)
        probs_cal = F.softmax(apply_temperature(logits, 2.0), dim=0)
        self.assertLess(probs_cal.max().item(), probs_uncal.max().item())

    def test_apply_temperature_invalid_zero(self):
        from backend.calibration import apply_temperature
        logits = torch.tensor([1.0, 2.0])
        result = apply_temperature(logits, 0.0)
        self.assertTrue(torch.allclose(result, logits))

    def test_calibration_registry_missing_file_defaults(self):
        from backend.calibration import CalibrationRegistry
        reg = CalibrationRegistry("/nonexistent/path/calibration.json")
        self.assertEqual(reg.get("anterior"), 1.0)
        self.assertEqual(reg.get("surface"), 1.0)
        self.assertFalse(reg.is_calibrated("anterior"))

    def test_calibration_registry_loads_file(self):
        from backend.calibration import CalibrationRegistry
        data = {"anterior": 1.42, "surface": 1.18}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(data, f)
            fpath = f.name
        try:
            reg = CalibrationRegistry(fpath)
            self.assertAlmostEqual(reg.get("anterior"), 1.42)
            self.assertAlmostEqual(reg.get("surface"), 1.18)
            self.assertTrue(reg.is_calibrated("anterior"))
        finally:
            os.unlink(fpath)

    def test_calibration_registry_save_and_reload(self):
        from backend.calibration import CalibrationRegistry
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "calibration.json")
            CalibrationRegistry.save(path, {"anterior": 1.55, "surface": 1.22})
            reg = CalibrationRegistry(path)
            self.assertAlmostEqual(reg.get("anterior"), 1.55)
            self.assertAlmostEqual(reg.get("surface"), 1.22)

    def test_temperature_scaler_forward(self):
        from backend.calibration import TemperatureScaler
        base = nn.Linear(4, 3)
        scaler = TemperatureScaler(base)
        x = torch.randn(2, 4)
        out_base = base(x)
        out_scaler = scaler(x)
        self.assertFalse(torch.allclose(out_base, out_scaler))


class TestUncertainty(unittest.TestCase):

    class _TinyDropoutModel(nn.Module):
        """A tiny model with dropout so MC-Dropout produces real variance."""
        def __init__(self, n_classes=3):
            super().__init__()
            self.net = nn.Sequential(
                nn.Linear(4, 16),
                nn.ReLU(),
                nn.Dropout(p=0.5),
                nn.Linear(16, n_classes),
            )
        def forward(self, x):
            return self.net(x)

    def test_mc_dropout_shape(self):
        from backend.uncertainty import mc_dropout_predict
        model = self._TinyDropoutModel(n_classes=3)
        x = torch.randn(1, 4)
        mean_probs, uncertainty = mc_dropout_predict(model, x, n_passes=5)
        self.assertEqual(mean_probs.shape, torch.Size([3]))
        self.assertIsInstance(uncertainty, float)
        self.assertGreaterEqual(uncertainty, 0.0)

    def test_mc_dropout_probs_sum_to_one(self):
        from backend.uncertainty import mc_dropout_predict
        model = self._TinyDropoutModel(n_classes=3)
        x = torch.randn(1, 4)
        mean_probs, _ = mc_dropout_predict(model, x, n_passes=10)
        self.assertAlmostEqual(mean_probs.sum().item(), 1.0, places=5)

    def test_mc_dropout_restores_eval_mode(self):
        from backend.uncertainty import mc_dropout_predict
        model = self._TinyDropoutModel()
        model.eval()
        x = torch.randn(1, 4)
        mc_dropout_predict(model, x)
        self.assertFalse(model.training)

    def test_needs_human_review_low_confidence(self):
        from backend.uncertainty import needs_human_review
        flagged, reasons = needs_human_review("Cataract", 0.60, 0.05)
        self.assertTrue(flagged)
        self.assertTrue(any("Confidence" in r for r in reasons))

    def test_needs_human_review_high_uncertainty(self):
        from backend.uncertainty import needs_human_review
        flagged, reasons = needs_human_review("Cataract", 0.85, 0.25)
        self.assertTrue(flagged)
        self.assertTrue(any("uncertainty" in r.lower() for r in reasons))

    def test_needs_human_review_critical_diagnosis_bar(self):
        from backend.uncertainty import needs_human_review
        flagged, reasons = needs_human_review("Uveitis", 0.80, 0.05)
        self.assertTrue(flagged)
        self.assertTrue(any("sight-threatening" in r.lower() or "Uveitis" in r for r in reasons))

    def test_needs_human_review_clears_for_confident_benign(self):
        from backend.uncertainty import needs_human_review
        flagged, reasons = needs_human_review("Conjunctivitis", 0.95, 0.02)
        self.assertFalse(flagged)
        self.assertEqual(reasons, [])

    def test_build_review_payload_shape(self):
        from backend.uncertainty import build_review_payload
        payload = build_review_payload("Jaundice", 0.50, 0.10)
        self.assertIn("requires_human_review", payload)
        self.assertIn("review_reasons", payload)
        self.assertIn("uncertainty", payload)
        self.assertIsInstance(payload["requires_human_review"], bool)
        self.assertIsInstance(payload["review_reasons"], list)


class TestClinicalCodes(unittest.TestCase):

    def test_all_diagnoses_have_entries(self):
        from backend.clinical_codes import CLINICAL_CODES
        expected = {"Cataract", "Conjunctivitis", "Eyelid", "Jaundice",
                    "Uveitis", "Normal", "Pterygium"}
        self.assertEqual(set(CLINICAL_CODES.keys()), expected)

    def test_icd10_codes_non_empty(self):
        from backend.clinical_codes import CLINICAL_CODES
        for name, entry in CLINICAL_CODES.items():
            self.assertIsNotNone(entry["icd10"], f"{name} missing ICD-10 code")
            self.assertGreater(len(entry["icd10"]), 0)

    def test_urgency_rank_range(self):
        from backend.clinical_codes import CLINICAL_CODES
        for name, entry in CLINICAL_CODES.items():
            self.assertIn(entry["urgency_rank"], range(5), f"{name} urgency_rank out of range")

    def test_emergency_conditions(self):
        from backend.clinical_codes import CLINICAL_CODES
        self.assertEqual(CLINICAL_CODES["Jaundice"]["urgency"], "emergency")
        self.assertEqual(CLINICAL_CODES["Uveitis"]["urgency"], "urgent")

    def test_normal_has_no_urgency(self):
        from backend.clinical_codes import CLINICAL_CODES
        self.assertEqual(CLINICAL_CODES["Normal"]["urgency"], "none")
        self.assertEqual(CLINICAL_CODES["Normal"]["urgency_rank"], 0)

    def test_escalation_message_for_critical(self):
        from backend.clinical_codes import CLINICAL_CODES
        self.assertIsNotNone(CLINICAL_CODES["Uveitis"]["escalation_message"])
        self.assertIsNotNone(CLINICAL_CODES["Jaundice"]["escalation_message"])

    def test_no_escalation_for_routine(self):
        from backend.clinical_codes import CLINICAL_CODES
        self.assertIsNone(CLINICAL_CODES["Cataract"]["escalation_message"])
        self.assertIsNone(CLINICAL_CODES["Normal"]["escalation_message"])

    def test_get_clinical_code_fallback(self):
        from backend.clinical_codes import get_clinical_code
        entry = get_clinical_code("UNKNOWN_DIAGNOSIS_XYZ")
        self.assertIn("urgency", entry)
        self.assertIsNotNone(entry["escalation_message"])  

    def test_is_critical(self):
        from backend.clinical_codes import is_critical
        self.assertTrue(is_critical("Uveitis"))
        self.assertTrue(is_critical("Jaundice"))
        self.assertFalse(is_critical("Normal"))
        self.assertFalse(is_critical("Cataract"))

    def test_sort_by_urgency(self):
        from backend.clinical_codes import sort_by_urgency
        diagnoses = ["Normal", "Cataract", "Uveitis", "Jaundice", "Conjunctivitis"]
        sorted_d = sort_by_urgency(diagnoses)
        self.assertEqual(sorted_d[0], "Jaundice")
        self.assertEqual(sorted_d[1], "Uveitis")
        self.assertEqual(sorted_d[-1], "Normal")


class TestAuth(unittest.TestCase):

    def test_hash_and_verify_password(self):
        from backend.auth import hash_password, verify_password
        plain = "Super$ecure123!"
        hashed = hash_password(plain)
        self.assertTrue(verify_password(plain, hashed))
        self.assertFalse(verify_password("wrong", hashed))

    def test_hashes_differ_for_same_input(self):
        from backend.auth import hash_password
        h1 = hash_password("mypassword")
        h2 = hash_password("mypassword")
        self.assertNotEqual(h1, h2)

    def test_create_and_decode_token(self):
        from backend.auth import create_access_token, decode_token
        token = create_access_token(subject="user-123", role="patient")
        payload = decode_token(token)
        self.assertEqual(payload["sub"], "user-123")
        self.assertEqual(payload["role"], "patient")

    def test_token_roles_preserved(self):
        from backend.auth import create_access_token, decode_token
        for role in ("patient", "clinician", "admin"):
            token = create_access_token(subject="u", role=role)
            payload = decode_token(token)
            self.assertEqual(payload["role"], role)

    def test_tampered_token_rejected(self):
        from backend.auth import create_access_token, decode_token
        from fastapi import HTTPException
        token = create_access_token(subject="u", role="patient")
        tampered = token[:-10] + "AAAAAAAAAA"
        with self.assertRaises(HTTPException):
            decode_token(tampered)

    def test_expired_token_rejected(self):
        from backend.auth import create_access_token, decode_token
        from fastapi import HTTPException
        token = create_access_token(subject="u", role="patient", expires_minutes=-1)
        with self.assertRaises(HTTPException):
            decode_token(token)


class TestModelRegistry(unittest.TestCase):

    def _make_session(self):
        """Creates a fresh in-memory SQLite DB for each test."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from backend.db import Base, ModelVersion, AuditLog, User, ScanResult, ClinicianOverride
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        Session = sessionmaker(bind=engine)
        return Session()

    def test_register_then_activate(self):
        from backend.model_registry import register_model, set_active, get_active
        db = self._make_session()
        mv = register_model(
            db=db, group_key="anterior", version_tag="v1.0",
            architecture="EfficientNet-B4", weights_path="/models/anterior.pth",
            val_accuracy=0.89, calibration_temperature=1.42,
        )
        self.assertFalse(mv.active)
        active = set_active(db, mv.id)
        self.assertTrue(active.active)
        retrieved = get_active(db, "anterior")
        self.assertEqual(retrieved.id, mv.id)

    def test_set_active_deactivates_previous(self):
        from backend.model_registry import register_model, set_active, get_active
        db = self._make_session()
        mv1 = register_model(db=db, group_key="surface", version_tag="v1",
                              architecture="EfficientNet-B4", weights_path="/m1.pth")
        mv2 = register_model(db=db, group_key="surface", version_tag="v2",
                              architecture="EfficientNet-B4", weights_path="/m2.pth")
        set_active(db, mv1.id)
        set_active(db, mv2.id)
        db.refresh(mv1)
        self.assertFalse(mv1.active)
        self.assertEqual(get_active(db, "surface").id, mv2.id)

    def test_rollback_to_previous(self):
        from backend.model_registry import register_model, set_active, rollback, get_active
        import time
        db = self._make_session()
        mv1 = register_model(db=db, group_key="surface", version_tag="v1",
                              architecture="EfficientNet-B4", weights_path="/m1.pth")
        time.sleep(0.01)
        mv2 = register_model(db=db, group_key="surface", version_tag="v2",
                              architecture="EfficientNet-B4", weights_path="/m2.pth")
        set_active(db, mv1.id)
        set_active(db, mv2.id)
        rolled = rollback(db, "surface")
        self.assertEqual(rolled.id, mv1.id)

    def test_get_active_returns_none_when_empty(self):
        from backend.model_registry import get_active
        db = self._make_session()
        self.assertIsNone(get_active(db, "anterior"))


class TestPredictResponseShape(unittest.TestCase):
    """Validates that the new clinical fields appear in /predict's JSON response
    by running the FastAPI test client with all models mocked away."""

    def _make_fake_image_bytes(self):
        img = Image.new("RGB", (100, 100), color=(128, 100, 90))
        buf = BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()

    def test_response_has_clinical_fields(self):
        """Smoke-test the /predict endpoint shape with a fake model response."""
        import importlib
        import backend.main as bm

        fake_router_logits = torch.zeros(1, 3)
        fake_router_logits[0, 2] = 5.0  

        class FakeRouter(nn.Module):
            def forward(self, x):
                return fake_router_logits

        fake_spec_logits = torch.zeros(1, 4)
        fake_spec_logits[0, 0] = 5.0  

        class FakeSpecialist(nn.Module):
            def forward(self, x):
                return fake_spec_logits
            features = [nn.Identity()]

        original_router = bm.ROUTER_MODEL
        original_specialists = bm.SPECIALIST_MODELS

        try:
            bm.ROUTER_MODEL = FakeRouter()
            bm.SPECIALIST_MODELS = {
                2: {
                    "type": "model",
                    "model": FakeSpecialist(),
                    "classes": ["Conjunctivitis", "Jaundice", "Normal", "Pterygium"],
                    "group_name": "Ocular Surface Disorders",
                }
            }

            from fastapi.testclient import TestClient
            client = TestClient(bm.app)

            img_bytes = self._make_fake_image_bytes()
            response = client.post(
                "/predict",
                files={"file": ("eye.jpg", img_bytes, "image/jpeg")},
                data={
                    "pain": "None", "vision": "No", "itch": "No",
                    "halos": "No", "discharge": "None",
                    "light_sens": "No", "floaters": "No", "duration": "Not Sure",
                },
            )

            self.assertIn(response.status_code, (200, 503))
            if response.status_code == 200:
                body = response.json()
                self.assertIn("diagnosis", body)
                self.assertIn("confidence", body)
                self.assertIn("icd10_code", body)
                self.assertIn("urgency", body)
                self.assertIn("urgency_rank", body)
                self.assertIn("requires_human_review", body)
                self.assertIn("uncertainty", body)
                self.assertIn("iqa_warnings", body)
                self.assertIn("hybrid_warnings_structured", body)
                for entry in body.get("hybrid_warnings_structured", []):
                    self.assertIn("severity", entry)
                    self.assertIn("message", entry)
        finally:
            bm.ROUTER_MODEL = original_router
            bm.SPECIALIST_MODELS = original_specialists


if __name__ == "__main__":
    unittest.main(verbosity=2)
