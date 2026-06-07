"""Authentication service with brute-force protection."""

from datetime import datetime, timedelta, timezone
from typing import Optional, Union
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.user import AdminUser, RefreshToken
from app.models.partner import PartnerUser
from app.security.auth import create_access_token, create_refresh_token
from app.security.password import verify_password

settings = get_settings()


class AuthError(Exception):
    pass


class AccountLockedError(AuthError):
    pass


async def _check_lockout(user: Union[AdminUser, PartnerUser]) -> None:
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        raise AccountLockedError("Conta temporariamente bloqueada. Tente novamente mais tarde.")


async def _record_failed_login(db: AsyncSession, user: Union[AdminUser, PartnerUser]) -> None:
    user.failed_login_attempts += 1
    if user.failed_login_attempts >= settings.login_max_attempts:
        user.locked_until = datetime.now(timezone.utc) + timedelta(
            minutes=settings.login_lockout_minutes
        )


async def _record_successful_login(db: AsyncSession, user: Union[AdminUser, PartnerUser]) -> None:
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)


async def authenticate_admin(
    db: AsyncSession, email: str, password: str
) -> tuple[AdminUser, str, str]:
    result = await db.execute(select(AdminUser).where(AdminUser.email == email, AdminUser.active.is_(True)))
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        if user:
            await _record_failed_login(db, user)
        raise AuthError("Credenciais inválidas")
    await _check_lockout(user)
    await _record_successful_login(db, user)
    access = create_access_token(user.email, "admin", user.id)
    refresh_plain, refresh_hash = create_refresh_token()
    token = RefreshToken(
        token_hash=refresh_hash,
        user_type="admin",
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    db.add(token)
    return user, access, refresh_plain


async def authenticate_partner_user(
    db: AsyncSession, email: str, password: str
) -> tuple[PartnerUser, str, str]:
    result = await db.execute(
        select(PartnerUser).where(PartnerUser.email == email, PartnerUser.active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user or not verify_password(password, user.password_hash):
        if user:
            await _record_failed_login(db, user)
        raise AuthError("Credenciais inválidas")
    await _check_lockout(user)
    await _record_successful_login(db, user)
    access = create_access_token(
        user.email, "partner", user.id, extra_claims={"partner_id": str(user.partner_id)}
    )
    refresh_plain, refresh_hash = create_refresh_token()
    token = RefreshToken(
        token_hash=refresh_hash,
        user_type="partner",
        user_id=user.id,
        expires_at=datetime.now(timezone.utc) + timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    db.add(token)
    return user, access, refresh_plain
