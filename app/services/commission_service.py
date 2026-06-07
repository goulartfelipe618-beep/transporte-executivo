"""Commission calculation and recording."""

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.booking import BookingReservation
from app.models.partner import PartnerCommission


def calculate_commission(amount: Decimal, percent: Decimal) -> Decimal:
    return (amount * percent / Decimal("100")).quantize(Decimal("0.01"))


async def calculate_and_record_commission(
    db: AsyncSession,
    reservation: BookingReservation,
) -> PartnerCommission:
    amount = reservation.total_amount or Decimal("0")
    percent = reservation.commission_percent or Decimal("0")
    commission_amount = calculate_commission(amount, percent)

    reservation.commission_amount = commission_amount

    commission = PartnerCommission(
        partner_id=reservation.partner_id,
        reservation_id=reservation.id,
        partner_name=reservation.partner_name or "",
        partner_token_snapshot=reservation.partner_token or "",
        commission_percent=percent,
        reservation_amount=amount,
        commission_amount=commission_amount,
        status="pending",
    )
    db.add(commission)
    await db.flush()
    return commission
