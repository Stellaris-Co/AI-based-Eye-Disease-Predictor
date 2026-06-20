"""
Encrypted object storage for scan images and heatmaps.

When scan history is enabled (DATABASE_URL is non-default and SCAN_STORAGE_BUCKET
is set), uploaded images and heatmaps are written to S3 (or any S3-compatible store
like GCS HMAC, MinIO, Cloudflare R2) with server-side encryption. The DB only stores
the object key; raw bytes never enter the DB.

When SCAN_STORAGE_BUCKET is NOT set, this module operates in stub mode: store()
returns None and fetch() returns None, so the rest of the codebase can call these
functions unconditionally without branching on storage availability. main.py treats
a None return from store() as "image not persisted" and omits image_path from the
scan record — correct behaviour for an operator who hasn't configured storage.

Privacy note: only store images if you have a legitimate reason and appropriate
user consent. The default configuration (no bucket configured) stores nothing, which
is the right default for a screening demo. See PRODUCTION.md and docs/INTENDED_USE.md
for guidance on when and how to enable persistence.
"""
from __future__ import annotations

import io
import os
from typing import Optional

from .logging_config import get_logger

logger = get_logger("storage")

BUCKET = os.getenv("SCAN_STORAGE_BUCKET", "")
KMS_KEY_ID = os.getenv("SCAN_STORAGE_KMS_KEY_ID", "")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
_client = None


def _get_client():
    global _client
    if _client is not None:
        return _client
    try:
        import boto3
        from botocore.config import Config
        _client = boto3.client(
            "s3",
            region_name=AWS_REGION,
            config=Config(signature_version="s3v4"),
        )
        return _client
    except ImportError:
        logger.warning(
            "storage.boto3_unavailable",
            message="boto3 is not installed — image storage is disabled. "
                    "Install boto3 if you want to persist scan images.",
        )
        return None


def store(
    data: bytes,
    key: str,
    content_type: str = "image/jpeg",
) -> Optional[str]:
    if not BUCKET:
        return None
    client = _get_client()
    if client is None:
        return None
    try:
        extra: dict = {"ServerSideEncryption": "aws:kms"}
        if KMS_KEY_ID:
            extra["SSEKMSKeyId"] = KMS_KEY_ID
        client.put_object(
            Bucket=BUCKET,
            Key=key,
            Body=data,
            ContentType=content_type,
            **extra,
        )
        logger.info("storage.stored", key=key, size_bytes=len(data))
        return key
    except Exception as exc:
        logger.error("storage.store_failed", key=key, error=str(exc))
        return None


def fetch(key: str) -> Optional[bytes]:
    if not BUCKET or not key:
        return None
    client = _get_client()
    if client is None:
        return None
    try:
        response = client.get_object(Bucket=BUCKET, Key=key)
        return response["Body"].read()
    except Exception as exc:
        logger.error("storage.fetch_failed", key=key, error=str(exc))
        return None


def presigned_url(key: str, expires_seconds: int = 300) -> Optional[str]:
    if not BUCKET or not key:
        return None
    client = _get_client()
    if client is None:
        return None
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": BUCKET, "Key": key},
            ExpiresIn=expires_seconds,
        )
    except Exception as exc:
        logger.error("storage.presign_failed", key=key, error=str(exc))
        return None


def is_configured() -> bool:
    return bool(BUCKET)
