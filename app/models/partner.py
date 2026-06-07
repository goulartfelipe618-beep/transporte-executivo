"""Partner models."""

import enum
import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.base import TimestampMixin, UUIDMixin

if TYPE_CHECKING:
    from app.models.booking import BookingReservation


class PartnerType(str, enum.Enum):
    HOTEL = "hotel"
    AGENCY = "agency"
    COMPANY = "company"
    EVENT_ORGANIZER = "event_organizer"
    CONCIERGE = "concierge"
    INFLUENCER = "influencer"
    AFFILIATE = "affiliate"


class Partner(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "partners"

    external_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    token: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    partner_type: Mapped[PartnerType] = mapped_column(
        Enum(PartnerType, name="partner_type_enum", create_constraint=True),
        default=PartnerType.AFFILIATE,
    )
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2), default=Decimal("10.00"))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    logo_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    banner_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    contact_phone: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)

    sessions: Mapped[List["PartnerSession"]] = relationship(back_populates="partner")
    commissions: Mapped[List["PartnerCommission"]] = relationship(back_populates="partner")
    payments: Mapped[List["PartnerPayment"]] = relationship(back_populates="partner")
    users: Mapped[List["PartnerUser"]] = relationship(back_populates="partner")
    reservations: Mapped[List["BookingReservation"]] = relationship(back_populates="partner")


class PartnerSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "partner_sessions"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), index=True
    )
    session_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    referrer: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    partner: Mapped["Partner"] = relationship(back_populates="sessions")


class PartnerCommission(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "partner_commissions"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), index=True
    )
    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("booking_reservations.id", ondelete="CASCADE"), unique=True
    )
    partner_name: Mapped[str] = mapped_column(String(255))
    partner_token_snapshot: Mapped[str] = mapped_column(String(128))
    commission_percent: Mapped[Decimal] = mapped_column(Numeric(5, 2))
    reservation_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    commission_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    partner: Mapped["Partner"] = relationship(back_populates="commissions")


class PartnerPayment(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "partner_payments"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    reference: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="pending")
    payment_method: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    partner: Mapped["Partner"] = relationship(back_populates="payments")


class PartnerUser(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "partner_users"

    partner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("partners.id", ondelete="CASCADE"), index=True
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    full_name: Mapped[str] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    failed_login_attempts: Mapped[int] = mapped_column(default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    partner: Mapped["Partner"] = relationship(back_populates="users")
