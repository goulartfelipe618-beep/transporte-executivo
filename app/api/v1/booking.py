"""Booking API endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.booking import (
    PassengerRequest,
    PaymentRequest,
    ReservationResponse,
    SearchRequest,
    VehicleSelectRequest,
)
from app.services import booking_service
from app.services.partner_service import get_partner_by_external_id

router = APIRouter(prefix="/booking", tags=["booking"])


async def _get_reservation_or_404(db: AsyncSession, reservation_id: UUID):
    reservation = await booking_service.get_reservation_by_id(db, reservation_id)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva não encontrada")
    return reservation


@router.post("/search", response_model=ReservationResponse)
async def search(
    data: SearchRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    partner = None
    partner_ext_id = request.session.get("partner_external_id")
    if partner_ext_id:
        partner = await get_partner_by_external_id(db, partner_ext_id)

    session_uuid = None
    if request.session.get("partner_session_id"):
        try:
            session_uuid = UUID(request.session["partner_session_id"])
        except ValueError:
            pass

    trip_type = data.trip_type.value
    if trip_type == "hourly":
        origin = data.city or ""
        destination = f"À disposição ({data.hourly_hours}h)"
        return_trip = False
    elif trip_type == "round_trip":
        origin = data.origin or ""
        destination = data.destination or ""
        return_trip = True
    else:
        origin = data.origin or ""
        destination = data.destination or ""
        return_trip = False

    reservation = await booking_service.create_search_reservation(
        db,
        partner=partner,
        trip_type=trip_type,
        origin=origin,
        destination=destination,
        trip_date=data.trip_date,
        trip_time=data.trip_time,
        passengers=data.passengers,
        luggage=data.luggage,
        return_trip=return_trip,
        return_date=data.return_date,
        return_time=data.return_time,
        city=data.city,
        hourly_hours=data.hourly_hours,
        notes=data.notes,
        session_id=session_uuid,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    request.session["reservation_id"] = str(reservation.id)
    return reservation


@router.get("/{reservation_id}/vehicles")
async def list_vehicles(
    reservation_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    reservation = await _get_reservation_or_404(db, reservation_id)
    vehicles = await booking_service.get_available_vehicles(
        reservation.origin,
        reservation.destination,
        reservation.passengers,
        reservation.luggage,
    )
    return {"items": vehicles}


@router.post("/{reservation_id}/vehicle", response_model=ReservationResponse)
async def select_vehicle(
    reservation_id: UUID,
    data: VehicleSelectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    reservation = await _get_reservation_or_404(db, reservation_id)
    vehicle_data = data.model_dump()
    await booking_service.select_vehicle(
        db,
        reservation,
        vehicle_data,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return reservation


@router.post("/{reservation_id}/passenger", response_model=ReservationResponse)
async def save_passenger(
    reservation_id: UUID,
    data: PassengerRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    reservation = await _get_reservation_or_404(db, reservation_id)
    await booking_service.save_passenger_data(
        db,
        reservation,
        data.full_name,
        data.phone,
        data.email,
        data.cpf,
        data.notes,
        whatsapp=data.whatsapp,
        company=data.company,
        flight_number=data.flight_number,
        lgpd_accepted=data.lgpd_accepted,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return reservation


@router.post("/{reservation_id}/payment")
async def initiate_payment(
    reservation_id: UUID,
    data: PaymentRequest,
    db: AsyncSession = Depends(get_db),
):
    reservation = await _get_reservation_or_404(db, reservation_id)
    payment = await booking_service.create_payment_intent(
        db, reservation, data.provider, data.method
    )
    return {
        "payment_id": str(payment.id),
        "provider": payment.provider,
        "method": payment.method,
        "amount": str(payment.amount),
        "status": payment.status,
        "checkout_url": f"/booking/{reservation_id}/pay/{payment.id}",
    }


@router.post("/{reservation_id}/confirm", response_model=ReservationResponse)
async def confirm(
    reservation_id: UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    reservation = await _get_reservation_or_404(db, reservation_id)
    if not reservation.payments:
        raise HTTPException(status_code=400, detail="Pagamento não iniciado")
    payment = reservation.payments[-1]
    reservation = await booking_service.confirm_reservation(
        db,
        reservation,
        payment,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    return reservation


@router.get("/code/{code}", response_model=ReservationResponse)
async def get_by_code(code: str, db: AsyncSession = Depends(get_db)):
    reservation = await booking_service.get_reservation_by_code(db, code)
    if not reservation:
        raise HTTPException(status_code=404, detail="Reserva não encontrada")
    return reservation
