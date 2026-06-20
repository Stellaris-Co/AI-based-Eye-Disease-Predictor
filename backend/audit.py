"""
Audit logging helper for OphthalmoAI.

Writes every significant event to two sinks simultaneously:
  1. The audit_logs database table (durable, queryable, survives log rotation)
  2. The structured logger (for real-time log aggregation via Loki/CloudWatch)

Call sites are intentionally simple — a single log_event() call, not two separate
write operations — so it's easy to be thorough rather than only auditing the paths
you remembered to add it to. The DB write is wrapped in a try/except so a broken
DB connection never prevents a request from completing; the structured log is
written regardless.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from .db import AuditLog
from .logging_config import get_logger

logger = get_logger("audit")


def log_event(
    db: Session,
    action: str,
    success: bool = True,
    user_id: Optional[str] = None,
    resource_id: Optional[str] = None,
    resource_type: Optional[str] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    error_detail: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """Writes one audit event to the DB and the structured logger.
    DB write failures are caught and logged but never re-raised — the audit
    trail failing to write should never cause a user-visible 500 error."""

    log_fn = logger.info if success else logger.warning
    log_fn(
        "audit.event",
        action=action,
        success=success,
        user_id=user_id,
        resource_id=resource_id,
        resource_type=resource_type,
        ip=ip_address,
        **(metadata or {}),
    )

    try:
        entry = AuditLog(
            action=action,
            success=success,
            user_id=user_id,
            resource_id=resource_id,
            resource_type=resource_type,
            ip_address=ip_address,
            user_agent=user_agent,
            error_detail=error_detail,
            metadata_=metadata,
        )
        db.add(entry)
        db.commit()
    except Exception as exc:
        logger.error(
            "audit.db_write_failed",
            action=action,
            error=str(exc),
        )
        db.rollback()
