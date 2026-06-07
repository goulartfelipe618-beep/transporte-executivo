"""Admin panel API."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_admin
from app.models.audit import AccessLog, AuditLog
from app.models.booking import BookingReservation
from app.models.partner import Partner, PartnerCommission, PartnerPayment
from app.models.user import AdminUser
from app.schemas.auth import LoginRequest, TokenResponse
from app.schemas.partner import PartnerCreate
from app.security.password import hash_password
from app.services.auth_service import AuthError, authenticate_admin

router = APIRouter(prefix="/api/admin", tags=["admin-panel"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        _, access, refresh = await authenticate_admin(db, data.email, data.password)
        return TokenResponse(access_token=access, refresh_token=refresh)
    except AuthError as e:
        raise HTTPException(status_code=401, detail=str(e)) from e


@router.get("/dashboard")
async def dashboard(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    partners_count = (await db.execute(select(func.count(Partner.id)))).scalar()
    reservations_count = (await db.execute(select(func.count(BookingReservation.id)))).scalar()
    commissions_total = (
        await db.execute(select(func.coalesce(func.sum(PartnerCommission.commission_amount), 0)))
    ).scalar()
    return {
        "partners": partners_count or 0,
        "reservations": reservations_count or 0,
        "commissions_total": str(commissions_total or 0),
    }


@router.get("/partners")
async def list_partners(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    result = await db.execute(select(Partner).offset(skip).limit(limit))
    return {
        "items": [
            {
                "id": str(p.id),
                "external_id": p.external_id,
                "name": p.name,
                "slug": p.slug,
                "active": p.active,
                "commission_percent": str(p.commission_percent),
            }
            for p in result.scalars().all()
        ]
    }


@router.post("/partners")
async def create_partner(
    data: PartnerCreate,
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    partner = Partner(
        external_id=data.external_id,
        name=data.name,
        slug=data.slug,
        token=data.token,
        partner_type=data.partner_type,
        commission_percent=data.commission_percent,
        logo_url=data.logo_url,
        banner_url=data.banner_url,
        contact_email=str(data.contact_email) if data.contact_email else None,
        active=True,
    )
    db.add(partner)
    await db.flush()
    audit = AuditLog(
        entity_type="partner",
        entity_id=partner.id,
        action="created",
        actor_type="admin",
        actor_id=admin.id,
        new_values={"external_id": partner.external_id, "name": partner.name},
        created_at=partner.created_at,
    )
    db.add(audit)
    return {"id": str(partner.id), "external_id": partner.external_id}


@router.get("/reservations")
async def list_reservations(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    result = await db.execute(
        select(BookingReservation).order_by(BookingReservation.created_at.desc()).offset(skip).limit(limit)
    )
    return {
        "items": [
            {
                "id": str(r.id),
                "code": r.code,
                "status": r.status,
                "partner_name": r.partner_name,
                "total_amount": str(r.total_amount) if r.total_amount else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in result.scalars().all()
        ]
    }


@router.get("/commissions")
async def list_commissions(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PartnerCommission).order_by(PartnerCommission.created_at.desc()).limit(200)
    )
    return {"items": [{"id": str(c.id), "amount": str(c.commission_amount), "status": c.status} for c in result.scalars()]}


@router.get("/logs/access")
async def access_logs(
    admin: AdminUser = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    limit: int = 100,
):
    result = await db.execute(select(AccessLog).order_by(AccessLog.created_at.desc()).limit(limit))
    return {
        "items": [
            {
                "path": l.path,
                "method": l.method,
                "status_code": l.status_code,
                "ip": l.ip_address,
                "created_at": l.created_at.isoformat(),
            }
            for l in result.scalars().all()
        ]
    }
