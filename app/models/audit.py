"""Audit and access log models."""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base
from app.models.base import UUIDMixin


class AccessLog(UUIDMixin, Base):
    __tablename__ = "access_logs"

    path: Mapped[str] = mapped_column(String(512))
    method: Mapped[str] = mapped_column(String(16))
    status_code: Mapped[int] = mapped_column()
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    user_agent: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    user_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    partner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AuditLog(UUIDMixin, Base):
    __tablename__ = "audit_logs"

    entity_type: Mapped[str] = mapped_column(String(64))
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    action: Mapped[str] = mapped_column(String(64))
    actor_type: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    actor_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True)
    old_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    new_values: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
