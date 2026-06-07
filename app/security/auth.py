"""JWT token management."""

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from uuid import UUID

from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


def create_access_token(
    subject: str,
    user_type: str,
    user_id: UUID,
    extra_claims: Optional[dict[str, Any]] = None,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.jwt_access_token_expire_minutes
    )
    payload = {
        "sub": subject,
        "type": "access",
        "user_type": user_type,
        "user_id": str(user_id),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token() -> tuple[str, str]:
    """Returns (plain token, hashed token for storage)."""
    plain = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(plain.encode()).hexdigest()
    return plain, token_hash


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


def verify_access_token(token: str) -> Optional[dict[str, Any]]:
    try:
        payload = decode_token(token)
        if payload.get("type") != "access":
            return None
        return payload
    except JWTError:
        return None
