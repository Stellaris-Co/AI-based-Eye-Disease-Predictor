"""
Model version registry for OphthalmoAI.

A thin layer over the model_versions DB table (backend/db.py) that provides:
  - register_model():  record a new trained checkpoint with its metrics
  - set_active():      promote a version to active (and deactivate all others in the group)
  - get_active():      look up which weights file + temperature to use for a given group
  - rollback():        revert to the previous active version

Also maintains a JSON sidecar (models/registry.json) so an operator can inspect
the registry without running Python, and so calibration temperatures can be loaded
by CalibrationRegistry (backend/calibration.py) even before the DB is available
(e.g. during local inference without a full postgres stack).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from .db import ModelVersion
from .logging_config import get_logger

logger = get_logger("model_registry")

REGISTRY_JSON_PATH = os.getenv(
    "MODEL_REGISTRY_JSON",
    os.path.join(os.path.dirname(__file__), "..", "models", "registry.json"),
)


def register_model(
    db: Session,
    group_key: str,
    version_tag: str,
    architecture: str,
    weights_path: str,
    val_accuracy: Optional[float] = None,
    val_auc: Optional[float] = None,
    val_sensitivity: Optional[Dict[str, float]] = None,
    val_specificity: Optional[Dict[str, float]] = None,
    val_set_description: Optional[str] = None,
    calibration_temperature: float = 1.0,
    calibration_ece: Optional[float] = None,
    registered_by: Optional[str] = None,
) -> ModelVersion:
    mv = ModelVersion(
        group_key=group_key,
        version_tag=version_tag,
        architecture=architecture,
        weights_path=weights_path,
        val_accuracy=val_accuracy,
        val_auc=val_auc,
        val_sensitivity=val_sensitivity,
        val_specificity=val_specificity,
        val_set_description=val_set_description,
        calibration_temperature=calibration_temperature,
        calibration_ece=calibration_ece,
        active=False,
        registered_by=registered_by,
    )
    db.add(mv)
    db.commit()
    db.refresh(mv)
    logger.info(
        "model_registry.registered",
        group=group_key,
        version=version_tag,
        architecture=architecture,
        id=mv.id,
    )
    _sync_json(db)
    return mv


def set_active(db: Session, version_id: str) -> ModelVersion:
    target = db.query(ModelVersion).filter(ModelVersion.id == version_id).first()
    if not target:
        raise ValueError(f"ModelVersion id={version_id!r} not found")

    db.query(ModelVersion).filter(
        ModelVersion.group_key == target.group_key,
        ModelVersion.id != version_id,
    ).update({"active": False})
    target.active = True
    db.commit()
    db.refresh(target)

    logger.info(
        "model_registry.activated",
        group=target.group_key,
        version=target.version_tag,
        id=target.id,
    )
    _sync_json(db)
    return target


def get_active(db: Session, group_key: str) -> Optional[ModelVersion]:
    return (
        db.query(ModelVersion)
        .filter(ModelVersion.group_key == group_key, ModelVersion.active == True)
        .first()
    )


def rollback(db: Session, group_key: str) -> Optional[ModelVersion]:
    current = get_active(db, group_key)
    if not current:
        logger.warning("model_registry.rollback_no_active", group=group_key)
        return None

    current.active = False
    db.flush()

    previous = (
        db.query(ModelVersion)
        .filter(
            ModelVersion.group_key == group_key,
            ModelVersion.id != current.id,
        )
        .order_by(ModelVersion.registered_at.desc())
        .first()
    )
    if previous:
        previous.active = True
        db.commit()
        logger.info(
            "model_registry.rolled_back",
            group=group_key,
            from_version=current.version_tag,
            to_version=previous.version_tag,
        )
        _sync_json(db)
        return previous

    current.active = True
    db.commit()
    logger.warning(
        "model_registry.rollback_no_previous",
        group=group_key,
        kept_version=current.version_tag,
    )
    return current


def list_versions(db: Session, group_key: Optional[str] = None) -> List[ModelVersion]:
    q = db.query(ModelVersion)
    if group_key:
        q = q.filter(ModelVersion.group_key == group_key)
    return q.order_by(ModelVersion.registered_at.desc()).all()


def _sync_json(db: Session) -> None:
    try:
        active_versions = (
            db.query(ModelVersion)
            .filter(ModelVersion.active == True)
            .all()
        )
        data: Dict = {
            "last_updated": datetime.now(timezone.utc).isoformat(),
            "active_versions": {},
            "calibration_temperatures": {},
        }
        for mv in active_versions:
            data["active_versions"][mv.group_key] = {
                "id": mv.id,
                "version_tag": mv.version_tag,
                "architecture": mv.architecture,
                "weights_path": mv.weights_path,
                "val_accuracy": mv.val_accuracy,
                "val_auc": mv.val_auc,
                "calibration_temperature": mv.calibration_temperature,
                "registered_at": mv.registered_at.isoformat() if mv.registered_at else None,
            }
            data["calibration_temperatures"][mv.group_key] = mv.calibration_temperature or 1.0

        os.makedirs(os.path.dirname(os.path.abspath(REGISTRY_JSON_PATH)), exist_ok=True)
        with open(REGISTRY_JSON_PATH, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as exc:
        logger.error("model_registry.json_sync_failed", error=str(exc))
