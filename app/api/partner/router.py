"""Partner panel API."""

from decimal import Decimal

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_partner_user
from app.models.booking import BookingReservation
from app.models.partner import PartnerCommission, PartnerUser
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth_service import AuthError, authenticate_partner_user

router = APIRouter(prefix="/api/partner", tags=["partner-panel"])


@router.post("/auth/login", response_model=TokenResponse)
async def login(data: LoginRequest, db: AsyncSession = Depends(get_db)):
    try:
        _, access, refresh = await authenticate_partner_user(db, data.email, data.password)
        return TokenResponse(access_token=access, refresh_token=refresh)
    except AuthError as e:
        from fastapi import HTTPException

        raise HTTPException(status_code=401, detail=str(e)) from e


@router.get("/dashboard")
async def dashboard(
    user: PartnerUser = Depends(get_current_partner_user),
    db: AsyncSession = Depends(get_db),
):
    reservations_q = await db.execute(
        select(func.count(BookingReservation.id)).where(
            BookingReservation.partner_id == user.partner_id,
            BookingReservation.status == "confirmed",
        )
    )
    sold_q = await db.execute(
        select(func.coalesce(func.sum(BookingReservation.total_amount), 0)).where(
            BookingReservation.partner_id == user.partner_id,
            BookingReservation.status == "confirmed",
        )
    )
    comm_q = await db.execute(
        select(func.coalesce(func.sum(PartnerCommission.commission_amount), 0)).where(
            PartnerCommission.partner_id == user.partner_id
        )
    )
    pending_q = await db.execute(
        select(func.coalesce(func.sum(PartnerCommission.commission_amount), 0)).where(
            PartnerCommission.partner_id == user.partner_id,
            PartnerCommission.status == "pending",
        )
    )
    return {
        "total_reservations": reservations_q.scalar() or 0,
        "total_sold": Decimal(str(sold_q.scalar() or 0)),
        "total_commissions": Decimal(str(comm_q.scalar() or 0)),
        "pending_commissions": Decimal(str(pending_q.scalar() or 0)),
    }


@router.get("/reservations")
async def list_reservations(
    user: PartnerUser = Depends(get_current_partner_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
):
    result = await db.execute(
        select(BookingReservation)
        .where(BookingReservation.partner_id == user.partner_id)
        .order_by(BookingReservation.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    items = result.scalars().all()
    return {
        "items": [
            {
                "code": r.code,
                "status": r.status,
                "origin": r.origin,
                "destination": r.destination,
                "total_amount": str(r.total_amount) if r.total_amount else None,
                "commission_amount": str(r.commission_amount) if r.commission_amount else None,
                "created_at": r.created_at.isoformat(),
            }
            for r in items
        ]
    }


@router.get("/commissions")
async def list_commissions(
    user: PartnerUser = Depends(get_current_partner_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(PartnerCommission)
        .where(PartnerCommission.partner_id == user.partner_id)
        .order_by(PartnerCommission.created_at.desc())
        .limit(100)
    )
    return {
        "items": [
            {
                "id": str(c.id),
                "reservation_amount": str(c.reservation_amount),
                "commission_percent": str(c.commission_percent),
                "commission_amount": str(c.commission_amount),
                "status": c.status,
                "created_at": c.created_at.isoformat(),
            }
            for c in result.scalars().all()
        ]
    }
