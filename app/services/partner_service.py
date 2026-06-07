"""Partner validation and session management."""

import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.partner import Partner, PartnerSession


class PartnerNotFoundError(Exception):
    pass


class PartnerInvalidTokenError(Exception):
    pass


class PartnerInactiveError(Exception):
    pass


async def validate_partner_link(
    db: AsyncSession,
    partner_external_id: str,
    partner_token: str,
) -> Partner:
    result = await db.execute(
        select(Partner).where(
            Partner.external_id == partner_external_id,
            Partner.active.is_(True),
        )
    )
    partner = result.scalar_one_or_none()
    if not partner:
        raise PartnerNotFoundError(f"Parceiro não encontrado: {partner_external_id}")
    if not secrets.compare_digest(partner.token, partner_token):
        raise PartnerInvalidTokenError("Token de parceiro inválido")
    if not partner.active:
        raise PartnerInactiveError("Parceiro inativo")
    return partner


async def create_partner_session(
    db: AsyncSession,
    partner: Partner,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    referrer: Optional[str] = None,
    ttl_hours: int = 24,
) -> PartnerSession:
    session = PartnerSession(
        partner_id=partner.id,
        session_key=secrets.token_urlsafe(32),
        ip_address=ip_address,
        user_agent=user_agent,
        referrer=referrer,
        expires_at=datetime.now(timezone.utc) + timedelta(hours=ttl_hours),
        active=True,
    )
    db.add(session)
    await db.flush()
    return session


async def get_partner_by_external_id(
    db: AsyncSession, external_id: str
) -> Optional[Partner]:
    result = await db.execute(
        select(Partner).where(Partner.external_id == external_id)
    )
    return result.scalar_one_or_none()
