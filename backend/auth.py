from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from passlib.context import CryptContext
from sqlalchemy.orm import Session

try:
    from jose import JWTError, jwt
    JOSE_AVAILABLE = True
except ImportError:
    JOSE_AVAILABLE = False

from .db import User, get_db
from .logging_config import get_logger
from .security import login_tracker, token_blacklist
from .validators import validate_email, validate_password_strength, validate_role_claim

logger = get_logger("auth")


SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_BEFORE_PRODUCTION_DEPLOYMENT")
ALGORITHM  = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

ROLE_HIERARCHY = {"patient": 0, "clinician": 1, "admin": 2}


pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token", auto_error=False)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    subject: str,
    role: str,
    extra_claims: Optional[dict] = None,
    expires_minutes: Optional[int] = None,
) -> str:
    if not JOSE_AVAILABLE:
        raise RuntimeError(
            "python-jose is not installed. "
            "Run: pip install python-jose[cryptography]"
        )
    now = datetime.now(timezone.utc)
    expire = now + timedelta(minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: dict = {
        "sub":  subject,
        "role": role,
        "jti":  str(uuid.uuid4()), 
        "iat":  now,
        "exp":  expire,
        **(extra_claims or {}),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    if not JOSE_AVAILABLE:
        raise RuntimeError("python-jose is not installed.")
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is invalid or has expired. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    jti = payload.get("jti")
    if jti and token_blacklist.is_revoked(jti):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    role_valid, role_or_err = validate_role_claim(payload.get("role"))
    if not role_valid:
        logger.warning("auth.invalid_role_claim", detail=role_or_err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token contains an invalid role claim.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return payload


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub", "")
        if not user_id:
            return None
        return db.query(User).filter(
            User.id == user_id, User.is_active == True  # noqa: E712
        ).first()
    except HTTPException:
        return None


def require_role(*roles: str):
    min_rank = min(ROLE_HIERARCHY.get(r, 0) for r in roles)

    async def _dep(
        token: Optional[str] = Depends(oauth2_scheme),
        db: Session = Depends(get_db),
    ) -> User:
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token is missing the subject claim.",
            )
        user = db.query(User).filter(
            User.id == user_id, User.is_active == True  
        ).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found or account is disabled.",
            )
        if ROLE_HIERARCHY.get(user.role, -1) < min_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Your role ('{user.role}') does not have permission for this resource. "
                    f"Required: one of {list(roles)}."
                ),
            )
        return user

    return _dep


def revoke_token(token: str) -> None:
    try:
        payload = jwt.decode(
            token, SECRET_KEY, algorithms=[ALGORITHM],
            options={"verify_exp": False},  
        )
        jti = payload.get("jti")
        exp = payload.get("exp", 0)
        if jti:
            token_blacklist.revoke(jti, float(exp))
            logger.info("auth.token_revoked", jti=jti[:8] + "…")
    except JWTError:
        pass 


def authenticate_user(
    db: Session,
    email: str,
    password: str,
) -> Tuple[Optional[User], Optional[str]]:
    email_valid, email_normalised = validate_email(email)
    if not email_valid:
        return None, "Invalid email or password."

    locked, remaining = login_tracker.is_locked(email_normalised)
    if locked:
        logger.warning(
            "auth.login_blocked_lockout",
            email_hash=login_tracker._key(email_normalised),
            seconds_remaining=remaining,
        )
        return None, (
            f"Account temporarily locked due to multiple failed attempts. "
            f"Try again in {remaining // 60 + 1} minute(s)."
        )

    user = db.query(User).filter(User.email == email_normalised).first()

    dummy_hash = "$2b$12$invalidhashpadding000000000000000000000000000000000000"
    password_ok = verify_password(
        password,
        user.hashed_password if user else dummy_hash,
    )

    if not user or not password_ok or not user.is_active:
        newly_locked, lockout_secs = login_tracker.record_failure(email_normalised)
        if newly_locked:
            return None, (
                f"Account locked for {lockout_secs // 60} minutes after too many "
                "failed attempts."
            )
        return None, "Invalid email or password."

    login_tracker.record_success(email_normalised)
    return user, None
