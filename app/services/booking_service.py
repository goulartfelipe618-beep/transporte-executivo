"""Booking flow business logic."""

import random
import string
import uuid
from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.master_api import MasterAPIClient, MasterAPIError
from app.models.booking import (
    BookingLog,
    BookingPassenger,
    BookingPayment,
    BookingReservation,
    ReservationStatus,
)
from app.models.partner import Partner, PartnerCommission
from app.security.sanitize import sanitize_cpf, sanitize_phone, sanitize_text
from app.services.commission_service import calculate_and_record_commission

TAX_RATE = Decimal("0.05")

# Fallback vehicles when Master API unavailable
DEFAULT_VEHICLES = [
    {
        "category": "Sedan Executivo",
        "name": "Sedan Executivo",
        "brand": "Mercedes-Benz",
        "model": "Classe E",
        "passengers": 3,
        "luggage": 3,
        "benefits": ["Ar-condicionado", "Água mineral", "Wi-Fi", "Motorista profissional"],
        "image_url": "/static/images/vehicles/sedan.svg",
        "price": 350.00,
    },
    {
        "category": "SUV Executivo",
        "name": "SUV Executivo",
        "brand": "Toyota",
        "model": "Corolla Cross",
        "passengers": 4,
        "luggage": 3,
        "benefits": ["Ar-condicionado", "Água", "Motorista profissional", "Monitoramento"],
        "image_url": "/static/images/vehicles/suv.svg",
        "price": 320.00,
    },
    {
        "category": "Van Executiva",
        "name": "Van Executiva",
        "brand": "Mercedes-Benz",
        "model": "Sprinter",
        "passengers": 10,
        "luggage": 10,
        "benefits": ["Ar-condicionado", "Tomadas USB", "Motorista profissional"],
        "image_url": "/static/images/vehicles/van.svg",
        "price": 750.00,
    },
    {
        "category": "Blindado",
        "name": "Blindado",
        "brand": "BMW",
        "model": "Série 7 Blindado",
        "passengers": 4,
        "luggage": 4,
        "benefits": ["Segurança reforçada", "Discrição", "Motorista treinado"],
        "image_url": "/static/images/vehicles/blindado.svg",
        "price": 1200.00,
    },
    {
        "category": "Micro-ônibus",
        "name": "Micro-ônibus",
        "brand": "Mercedes-Benz",
        "model": "Volare",
        "passengers": 20,
        "luggage": 20,
        "benefits": ["Eventos", "Grupos médios", "Ar-condicionado"],
        "image_url": "/static/images/vehicles/micro.svg",
        "price": 1500.00,
    },
    {
        "category": "Ônibus",
        "name": "Ônibus",
        "brand": "Mercedes-Benz",
        "model": "O500",
        "passengers": 45,
        "luggage": 45,
        "benefits": ["Grandes grupos", "Eventos corporativos"],
        "image_url": "/static/images/vehicles/onibus.svg",
        "price": 2800.00,
    },
]


def estimate_route(origin: str, destination: str) -> tuple[Decimal, int]:
    """Estimativa de distância e duração (refinável com API de mapas)."""
    combined = f"{origin}|{destination}"
    seed = sum(ord(c) for c in combined)
    distance = Decimal(str(15 + (seed % 85)))
    duration = int(30 + (seed % 90))
    return distance, duration


def generate_reservation_code() -> str:
    prefix = "NX"
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=8))
    return f"{prefix}{suffix}"


async def log_booking_action(
    db: AsyncSession,
    reservation_id: uuid.UUID,
    action: str,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    log = BookingLog(
        reservation_id=reservation_id,
        action=action,
        details=details,
        ip_address=ip_address,
        user_agent=user_agent,
        created_at=datetime.now(timezone.utc),
    )
    db.add(log)


async def create_search_reservation(
    db: AsyncSession,
    partner: Optional[Partner],
    trip_type: str,
    origin: str,
    destination: str,
    trip_date: date,
    trip_time: time,
    passengers: int,
    luggage: int,
    return_trip: bool = False,
    return_date: Optional[date] = None,
    return_time: Optional[time] = None,
    city: Optional[str] = None,
    hourly_hours: Optional[int] = None,
    notes: Optional[str] = None,
    session_id: Optional[uuid.UUID] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BookingReservation:
    distance_km, duration_min = estimate_route(origin, destination)
    reservation = BookingReservation(
        code=generate_reservation_code(),
        status=ReservationStatus.SEARCH.value,
        trip_type=trip_type,
        origin=sanitize_text(origin, 512),
        destination=sanitize_text(destination, 512),
        city=sanitize_text(city, 255) if city else None,
        hourly_hours=hourly_hours,
        search_notes=sanitize_text(notes or "", 2000) or None,
        distance_km=distance_km,
        duration_minutes=duration_min,
        trip_date=trip_date,
        trip_time=trip_time,
        passengers=passengers,
        luggage=luggage,
        return_trip=return_trip,
        return_date=return_date,
        return_time=return_time,
        session_id=session_id,
    )
    if partner:
        reservation.partner_id = partner.id
        reservation.partner_external_id = partner.external_id
        reservation.partner_token = partner.token
        reservation.partner_name = partner.name
        reservation.commission_percent = partner.commission_percent

    db.add(reservation)
    await db.flush()
    await log_booking_action(
        db, reservation.id, "search_created", {"origin": origin, "destination": destination},
        ip_address, user_agent,
    )
    return reservation


async def get_available_vehicles(
    origin: str,
    destination: str,
    passengers: int,
    luggage: int,
) -> list[dict[str, Any]]:
    client = MasterAPIClient()
    try:
        vehicles = await client.get_vehicles(origin, destination, passengers, luggage)
        if vehicles:
            return vehicles
    except MasterAPIError:
        pass
    return [
        v for v in DEFAULT_VEHICLES
        if v["passengers"] >= passengers and v["luggage"] >= luggage
    ]


def _calculate_price(reservation: BookingReservation, base_price: Decimal) -> tuple[Decimal, Decimal, Decimal]:
    price = base_price
    if reservation.trip_type == "hourly" and reservation.hourly_hours:
        price = base_price * Decimal(reservation.hourly_hours) / Decimal("4")
    elif reservation.return_trip or reservation.trip_type == "round_trip":
        price *= Decimal("1.8")
    taxes = (price * TAX_RATE).quantize(Decimal("0.01"))
    total = (price + taxes).quantize(Decimal("0.01"))
    return price.quantize(Decimal("0.01")), taxes, total


async def select_vehicle(
    db: AsyncSession,
    reservation: BookingReservation,
    vehicle_data: dict[str, Any],
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BookingReservation:
    base = Decimal(str(vehicle_data.get("price", 0)))
    subtotal, taxes, total = _calculate_price(reservation, base)

    reservation.vehicle_category = vehicle_data.get("category")
    reservation.vehicle_brand = vehicle_data.get("brand")
    reservation.vehicle_model = vehicle_data.get("model")
    reservation.vehicle_name = vehicle_data.get("name")
    reservation.vehicle_image_url = vehicle_data.get("image_url")
    reservation.vehicle_benefits = {"benefits": vehicle_data.get("benefits", [])}
    reservation.subtotal = subtotal
    reservation.taxes_amount = taxes
    reservation.total_amount = total
    reservation.status = ReservationStatus.VEHICLE_SELECTED.value

    await log_booking_action(
        db, reservation.id, "vehicle_selected",
        {"vehicle": vehicle_data.get("name"), "price": str(total)},
        ip_address, user_agent,
    )
    return reservation


async def save_passenger_data(
    db: AsyncSession,
    reservation: BookingReservation,
    full_name: str,
    phone: str,
    email: str,
    cpf: str,
    notes: Optional[str] = None,
    whatsapp: Optional[str] = None,
    company: Optional[str] = None,
    flight_number: Optional[str] = None,
    lgpd_accepted: bool = False,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BookingPassenger:
    existing = await db.execute(
        select(BookingPassenger).where(BookingPassenger.reservation_id == reservation.id)
    )
    passenger = existing.scalar_one_or_none()
    data = {
        "full_name": sanitize_text(full_name, 255),
        "phone": sanitize_phone(phone),
        "whatsapp": sanitize_phone(whatsapp) if whatsapp else None,
        "email": sanitize_text(email, 255).lower(),
        "cpf": sanitize_cpf(cpf),
        "company": sanitize_text(company, 255) if company else None,
        "flight_number": sanitize_text(flight_number, 32) if flight_number else None,
        "lgpd_accepted": lgpd_accepted,
        "notes": sanitize_text(notes or "", 2000) or None,
    }
    if passenger:
        for k, v in data.items():
            setattr(passenger, k, v)
    else:
        passenger = BookingPassenger(reservation_id=reservation.id, **data)
        db.add(passenger)

    reservation.status = ReservationStatus.PASSENGER_FILLED.value
    await log_booking_action(db, reservation.id, "passenger_filled", ip_address=ip_address, user_agent=user_agent)
    return passenger


async def create_payment_intent(
    db: AsyncSession,
    reservation: BookingReservation,
    provider: str,
    method: str,
) -> BookingPayment:
    payment = BookingPayment(
        reservation_id=reservation.id,
        provider=provider,
        method=method,
        amount=reservation.total_amount or Decimal("0"),
        status="pending",
    )
    db.add(payment)
    reservation.status = ReservationStatus.PAYMENT_PENDING.value
    await db.flush()
    return payment


async def confirm_reservation(
    db: AsyncSession,
    reservation: BookingReservation,
    payment: BookingPayment,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> BookingReservation:
    payment.status = "paid"
    payment.paid_at = datetime.now(timezone.utc)
    reservation.status = ReservationStatus.CONFIRMED.value
    reservation.confirmed_at = datetime.now(timezone.utc)
    reservation.qr_code_data = f"NEXUS:{reservation.code}"

    if reservation.partner_id and reservation.total_amount:
        await calculate_and_record_commission(db, reservation)

    await log_booking_action(db, reservation.id, "confirmed", ip_address=ip_address, user_agent=user_agent)

    client = MasterAPIClient()
    try:
        payload = {
            "reservation_code": reservation.code,
            "partner_id": reservation.partner_external_id,
            "origin": reservation.origin,
            "destination": reservation.destination,
            "trip_date": reservation.trip_date.isoformat(),
            "trip_time": reservation.trip_time.isoformat(),
            "vehicle": reservation.vehicle_name,
            "total_amount": str(reservation.total_amount),
            "passengers": reservation.passengers,
        }
        result = await client.send_reservation_webhook(payload)
        reservation.master_sync_status = "synced"
        reservation.master_reference = result.get("reference") if result else None
    except MasterAPIError:
        reservation.master_sync_status = "pending_retry"

    return reservation


async def get_reservation_by_code(db: AsyncSession, code: str) -> Optional[BookingReservation]:
    result = await db.execute(
        select(BookingReservation).where(BookingReservation.code == code.upper())
    )
    return result.scalar_one_or_none()


async def get_reservation_by_id(db: AsyncSession, reservation_id: uuid.UUID) -> Optional[BookingReservation]:
    result = await db.execute(
        select(BookingReservation).where(BookingReservation.id == reservation_id)
    )
    return result.scalar_one_or_none()
