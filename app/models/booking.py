"""Booking models."""

import enum
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, Numeric, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.partner import Partner


class TripType(str, enum.Enum):
    ONE_WAY = "one_way"
    ROUND_TRIP = "round_trip"
    HOURLY = "hourly"


class ReservationStatus(str, enum.Enum):
    DRAFT = "draft"
    SEARCH = "search"
    VEHICLE_SELECTED = "vehicle_selected"
    PASSENGER_FILLED = "passenger_filled"
    PAYMENT_PENDING = "payment_pending"
    PAYMENT_PROCESSING = "payment_processing"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class BookingReservation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "booking_reservations"

    code: Mapped[str] = mapped_column(String(16), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(32), default=ReservationStatus.DRAFT.value)

    partner_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="SET NULL"), index=True, nullable=True
    )
    partner_external_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    partner_token: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    partner_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    commission_percent: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 2), nullable=True)
    commission_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)

    trip_type: Mapped[str] = mapped_column(String(32), default=TripType.ONE_WAY.value)
    origin: Mapped[str] = mapped_column(String(512))
    destination: Mapped[str] = mapped_column(String(512))
    city: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    hourly_hours: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    search_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    distance_km: Mapped[Optional[Decimal]] = mapped_column(Numeric(8, 2), nullable=True)
    duration_minutes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    trip_date: Mapped[date] = mapped_column(Date)
    trip_time: Mapped[time] = mapped_column(Time)
    return_trip: Mapped[bool] = mapped_column(Boolean, default=False)
    return_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    return_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    passengers: Mapped[int] = mapped_column(Integer, default=1)
    luggage: Mapped[int] = mapped_column(Integer, default=0)

    vehicle_category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    vehicle_brand: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    vehicle_model: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    vehicle_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    vehicle_image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    vehicle_benefits: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)

    subtotal: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    taxes_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    total_amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")

    master_sync_status: Mapped[str] = mapped_column(String(32), default="pending")
    master_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)

    confirmed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    qr_code_data: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    partner: Mapped[Optional["Partner"]] = relationship(back_populates="reservations")
    passenger: Mapped[Optional["BookingPassenger"]] = relationship(
        back_populates="reservation", uselist=False
    )
    payments: Mapped[List["BookingPayment"]] = relationship(back_populates="reservation")
    logs: Mapped[List["BookingLog"]] = relationship(back_populates="reservation")


class BookingPassenger(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "booking_passengers"

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("booking_reservations.id", ondelete="CASCADE"),
        unique=True,
    )
    full_name: Mapped[str] = mapped_column(String(255))
    phone: Mapped[str] = mapped_column(String(32))
    whatsapp: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    email: Mapped[str] = mapped_column(String(255))
    cpf: Mapped[str] = mapped_column(String(14))
    company: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    flight_number: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    lgpd_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    reservation: Mapped["BookingReservation"] = relationship(back_populates="passenger")


class BookingPayment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "booking_payments"

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("booking_reservations.id", ondelete="CASCADE"), index=True
    )
    provider: Mapped[str] = mapped_column(String(32))
    method: Mapped[str] = mapped_column(String(32))
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    external_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    provider_response: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    reservation: Mapped["BookingReservation"] = relationship(back_populates="payments")


class BookingLog(UUIDMixin, Base):
    __tablename__ = "booking_logs"

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("booking_reservations.id", ondelete="CASCADE"), index=True
    )
    action: Mapped[str] = mapped_column(String(64))
    details: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    reservation: Mapped["BookingReservation"] = relationship(back_populates="logs")
