"""FastAPI dependencies."""

from typing import Annotated, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.user import AdminUser
from app.models.partner import PartnerUser
from app.security.auth import verify_access_token
from sqlalchemy import select

security = HTTPBearer(auto_error=False)


async def get_current_admin(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AdminUser:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    payload = verify_access_token(credentials.credentials)
    if not payload or payload.get("user_type") != "admin":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user_id = UUID(payload["user_id"])
    result = await db.execute(select(AdminUser).where(AdminUser.id == user_id, AdminUser.active.is_(True)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user


async def get_current_partner_user(
    credentials: Annotated[Optional[HTTPAuthorizationCredentials], Depends(security)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PartnerUser:
    if not credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autenticado")
    payload = verify_access_token(credentials.credentials)
    if not payload or payload.get("user_type") != "partner":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido")
    user_id = UUID(payload["user_id"])
    result = await db.execute(
        select(PartnerUser).where(PartnerUser.id == user_id, PartnerUser.active.is_(True))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Usuário não encontrado")
    return user


def get_session_partner_id(request: Request) -> Optional[str]:
    return request.session.get("partner_external_id")
