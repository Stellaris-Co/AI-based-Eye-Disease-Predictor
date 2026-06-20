"""
Database models for OphthalmoAI.

Uses SQLAlchemy Core + declarative mapping so the same models work with any
backend (SQLite for dev/testing, PostgreSQL for staging/production).  The DB URL
is read from the DATABASE_URL environment variable; it defaults to a local SQLite
file so a fresh clone with no env vars still boots and passes tests without any
external services.

Tables:
  users              — authentication + role management
  scan_results       — every /predict call, with full clinical metadata
  clinician_overrides — second-opinion / override entries tied to scan results
  audit_logs         — immutable append-only event trail (auth, predictions, overrides)
  model_versions     — model registry (architecture, path, metrics, calibration T)
"""
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON,
    String, Text, create_engine, event,
)
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./ophthalmoai.db",
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {},
    echo=False,
)

if DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragmas(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class User(Base):
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    role = Column(String(32), nullable=False, default="patient")
    # role values: "patient" | "clinician" | "admin"
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    last_login_at = Column(DateTime(timezone=True), nullable=True)

    scans = relationship("ScanResult", back_populates="user", cascade="all, delete-orphan")
    overrides = relationship(
        "ClinicianOverride", foreign_keys="ClinicianOverride.clinician_id",
        back_populates="clinician"
    )
    audit_entries = relationship("AuditLog", back_populates="user")

    def __repr__(self):
        return f"<User {self.email} role={self.role}>"


class ScanResult(Base):
    __tablename__ = "scan_results"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    diagnosis = Column(String(100), nullable=False, index=True)
    confidence = Column(Float, nullable=False)          
    group_name = Column(String(100), nullable=True)
    probabilities = Column(JSON, nullable=True)         

    calibrated = Column(Boolean, nullable=False, default=False)
    calibration_temperature = Column(Float, nullable=True)
    uncertainty = Column(Float, nullable=True)          
    requires_human_review = Column(Boolean, nullable=False, default=False)
    review_reasons = Column(JSON, nullable=True)         

    icd10_code = Column(String(20), nullable=True)
    snomed_code = Column(String(20), nullable=True)
    urgency = Column(String(32), nullable=True)          
    urgency_rank = Column(Integer, nullable=True)        

    hybrid_warnings = Column(JSON, nullable=True)     
    hybrid_warnings_structured = Column(JSON, nullable=True)  

    iqa_acceptable = Column(Boolean, nullable=True)
    iqa_warnings = Column(JSON, nullable=True)         

    symptoms_reported = Column(JSON, nullable=True)     

    model_version_id = Column(String(36), ForeignKey("model_versions.id", ondelete="SET NULL"), nullable=True)
    router_group_idx = Column(Integer, nullable=True)

    image_path = Column(String(500), nullable=True)
    heatmap_path = Column(String(500), nullable=True)

    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    user = relationship("User", back_populates="scans")
    override = relationship("ClinicianOverride", back_populates="scan", uselist=False)
    model_version = relationship("ModelVersion", back_populates="scans")

    def __repr__(self):
        return f"<ScanResult {self.id} {self.diagnosis} {self.confidence:.1f}%>"


class ClinicianOverride(Base):

    __tablename__ = "clinician_overrides"

    id = Column(String(36), primary_key=True, default=_uuid)
    scan_id = Column(String(36), ForeignKey("scan_results.id", ondelete="CASCADE"), nullable=False, unique=True)
    clinician_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    verdict = Column(String(32), nullable=False)

    corrected_diagnosis = Column(String(100), nullable=True)  
    corrected_icd10 = Column(String(20), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)

    scan = relationship("ScanResult", back_populates="override")
    clinician = relationship("User", foreign_keys=[clinician_id], back_populates="overrides")

    def __repr__(self):
        return f"<ClinicianOverride scan={self.scan_id} verdict={self.verdict}>"


class AuditLog(Base):

    __tablename__ = "audit_logs"

    id = Column(String(36), primary_key=True, default=_uuid)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)

    action = Column(String(100), nullable=False, index=True)

    resource_id = Column(String(36), nullable=True, index=True) 
    resource_type = Column(String(50), nullable=True)             

    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)

    success = Column(Boolean, nullable=False, default=True)
    error_detail = Column(Text, nullable=True)

    metadata_ = Column("metadata", JSON, nullable=True)

    timestamp = Column(DateTime(timezone=True), nullable=False, default=_utcnow, index=True)

    user = relationship("User", back_populates="audit_entries")

    def __repr__(self):
        return f"<AuditLog {self.action} user={self.user_id} ok={self.success}>"


class ModelVersion(Base):

    __tablename__ = "model_versions"

    id = Column(String(36), primary_key=True, default=_uuid)
    group_key = Column(String(50), nullable=False, index=True)

    version_tag = Column(String(50), nullable=False)      
    architecture = Column(String(100), nullable=False)   
    weights_path = Column(String(500), nullable=False)    

    val_accuracy = Column(Float, nullable=True)
    val_auc = Column(Float, nullable=True)
    val_sensitivity = Column(JSON, nullable=True)   
    val_specificity = Column(JSON, nullable=True)   
    val_set_description = Column(Text, nullable=True)

    calibration_temperature = Column(Float, nullable=True, default=1.0)
    calibration_ece = Column(Float, nullable=True)  

    active = Column(Boolean, nullable=False, default=False, index=True)

    registered_at = Column(DateTime(timezone=True), nullable=False, default=_utcnow)
    registered_by = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    scans = relationship("ScanResult", back_populates="model_version")

    def __repr__(self):
        return f"<ModelVersion {self.group_key} {self.version_tag} active={self.active}>"


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
