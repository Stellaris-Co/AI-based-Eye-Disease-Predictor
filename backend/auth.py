"""
Authentication and role-based access control for OphthalmoAI.

Provides:
  - Password hashing (bcrypt via passlib)
  - JWT creation and verification (python-jose)
  - FastAPI dependency functions: get_current_user, require_role
  - Token endpoint helper: create_access_token

SECRET_KEY and ALGORITHM are read from environment variables. The app refuses to
start if SECRET_KEY is the default insecure placeholder in any non-development mode
(enforced in main.py's lifespan, not here, so this module stays testable in isolation).

Role hierarchy (lowest → highest privilege):
  patient  → can submit scans, use chat, view their own results
  clinician → same as patient + can view and override any scan result
  admin     → same as clinician + can manage users, registry, and view audit logs
"""
from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import List, Optional

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

logger = get_logger("auth")

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "CHANGE_ME_BEFORE_PRODUCTION_DEPLOYMENT")
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "480"))

ROLE_HIERARCHY = {"patient": 0, "clinician": 1, "admin": 2}

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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
            "python-jose is not installed. Install it: pip install python-jose[cryptography]"
        )
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=expires_minutes or ACCESS_TOKEN_EXPIRE_MINUTES
    )
    payload = {"sub": subject, "role": role, "exp": expire, **(extra_claims or {})}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    if not JOSE_AVAILABLE:
        raise RuntimeError("python-jose is not installed.")
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid or expired token: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if not token:
        return None
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            return None
        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        return user
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
                detail="Not authenticated",
                headers={"WWW-Authenticate": "Bearer"},
            )
        payload = decode_token(token)
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

        user_rank = ROLE_HIERARCHY.get(user.role, -1)
        if user_rank < min_rank:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{user.role}' does not have permission. Required: one of {list(roles)}.",
            )
        return user

    return _dep


def authenticate_user(db: Session, email: str, password: str) -> Optional[User]:
    user = db.query(User).filter(User.email == email.lower().strip()).first()
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user
