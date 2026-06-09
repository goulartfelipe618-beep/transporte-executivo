"""Modelo SQLAlchemy da tabela master_admin_sessions (espelho Supabase)."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MasterAdminSession(Base):
    __tablename__ = "master_admin_sessions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    admin_id: Mapped[str] = mapped_column(String(64), index=True)
    admin_email: Mapped[str] = mapped_column(String(255))
    admin_nome: Mapped[str] = mapped_column(String(255), default="")
    admin_perfil: Mapped[str] = mapped_column(String(128), default="")
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
