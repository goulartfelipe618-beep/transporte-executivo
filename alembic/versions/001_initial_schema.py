"""Initial schema

Revision ID: 001
Revises:
Create Date: 2026-06-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

partner_type_enum = postgresql.ENUM(
    "hotel", "agency", "company", "event_organizer",
    "concierge", "influencer", "affiliate",
    name="partner_type_enum",
    create_type=False,
)


def upgrade() -> None:
    op.execute(
        "CREATE TYPE partner_type_enum AS ENUM ("
        "'hotel', 'agency', 'company', 'event_organizer', "
        "'concierge', 'influencer', 'affiliate')"
    )

    op.create_table(
        "partners",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("external_id", sa.String(64), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("slug", sa.String(128), nullable=False),
        sa.Column("token", sa.String(128), nullable=False),
        sa.Column("partner_type", partner_type_enum, nullable=False),
        sa.Column("commission_percent", sa.Numeric(5, 2), server_default="10.00"),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("logo_url", sa.String(512)),
        sa.Column("banner_url", sa.String(512)),
        sa.Column("contact_email", sa.String(255)),
        sa.Column("contact_phone", sa.String(32)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_partners_external_id", "partners", ["external_id"], unique=True)
    op.create_index("ix_partners_slug", "partners", ["slug"], unique=True)
    op.create_index("ix_partners_token", "partners", ["token"])

    op.create_table(
        "partner_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE")),
        sa.Column("session_key", sa.String(128), nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("referrer", sa.String(512)),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_partner_sessions_session_key", "partner_sessions", ["session_key"], unique=True)

    op.create_table(
        "admin_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("role", sa.String(32), server_default="admin"),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_admin_users_email", "admin_users", ["email"], unique=True)

    op.create_table(
        "partner_users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE")),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("active", sa.Boolean(), server_default="true"),
        sa.Column("last_login_at", sa.DateTime(timezone=True)),
        sa.Column("failed_login_attempts", sa.Integer(), server_default="0"),
        sa.Column("locked_until", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_partner_users_email", "partner_users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("token_hash", sa.String(255), nullable=False),
        sa.Column("user_type", sa.String(16), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean(), server_default="false"),
        sa.Column("replaced_by", postgresql.UUID(as_uuid=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)

    op.create_table(
        "booking_reservations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), server_default="draft"),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="SET NULL")),
        sa.Column("partner_external_id", sa.String(64)),
        sa.Column("partner_token", sa.String(128)),
        sa.Column("partner_name", sa.String(255)),
        sa.Column("commission_percent", sa.Numeric(5, 2)),
        sa.Column("commission_amount", sa.Numeric(12, 2)),
        sa.Column("origin", sa.String(512), nullable=False),
        sa.Column("destination", sa.String(512), nullable=False),
        sa.Column("trip_date", sa.Date(), nullable=False),
        sa.Column("trip_time", sa.Time(), nullable=False),
        sa.Column("return_trip", sa.Boolean(), server_default="false"),
        sa.Column("return_date", sa.Date()),
        sa.Column("return_time", sa.Time()),
        sa.Column("passengers", sa.Integer(), server_default="1"),
        sa.Column("luggage", sa.Integer(), server_default="0"),
        sa.Column("vehicle_category", sa.String(64)),
        sa.Column("vehicle_name", sa.String(128)),
        sa.Column("vehicle_image_url", sa.String(512)),
        sa.Column("vehicle_benefits", postgresql.JSONB()),
        sa.Column("subtotal", sa.Numeric(12, 2)),
        sa.Column("total_amount", sa.Numeric(12, 2)),
        sa.Column("currency", sa.String(3), server_default="BRL"),
        sa.Column("master_sync_status", sa.String(32), server_default="pending"),
        sa.Column("master_reference", sa.String(128)),
        sa.Column("session_id", postgresql.UUID(as_uuid=True)),
        sa.Column("confirmed_at", sa.DateTime(timezone=True)),
        sa.Column("qr_code_data", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_booking_reservations_code", "booking_reservations", ["code"], unique=True)

    op.create_table(
        "booking_passengers",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("booking_reservations.id", ondelete="CASCADE"), unique=True),
        sa.Column("full_name", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(32), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("cpf", sa.String(14), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "booking_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("booking_reservations.id", ondelete="CASCADE")),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("method", sa.String(32), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("external_id", sa.String(128)),
        sa.Column("provider_response", postgresql.JSONB()),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "booking_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("booking_reservations.id", ondelete="CASCADE")),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("details", postgresql.JSONB()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "partner_commissions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE")),
        sa.Column("reservation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("booking_reservations.id", ondelete="CASCADE"), unique=True),
        sa.Column("partner_name", sa.String(255), nullable=False),
        sa.Column("partner_token_snapshot", sa.String(128), nullable=False),
        sa.Column("commission_percent", sa.Numeric(5, 2), nullable=False),
        sa.Column("reservation_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("commission_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("paid_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "partner_payments",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("partners.id", ondelete="CASCADE")),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("reference", sa.String(128), nullable=False),
        sa.Column("status", sa.String(32), server_default="pending"),
        sa.Column("payment_method", sa.String(64)),
        sa.Column("notes", sa.Text()),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "access_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("path", sa.String(512), nullable=False),
        sa.Column("method", sa.String(16), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("user_type", sa.String(16)),
        sa.Column("user_id", postgresql.UUID(as_uuid=True)),
        sa.Column("partner_id", postgresql.UUID(as_uuid=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("entity_type", sa.String(64), nullable=False),
        sa.Column("entity_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("action", sa.String(64), nullable=False),
        sa.Column("actor_type", sa.String(16)),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True)),
        sa.Column("old_values", postgresql.JSONB()),
        sa.Column("new_values", postgresql.JSONB()),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_entity_id", "audit_logs", ["entity_id"])


def downgrade() -> None:
    for table in [
        "audit_logs", "access_logs", "partner_payments", "partner_commissions",
        "booking_logs", "booking_payments", "booking_passengers", "booking_reservations",
        "refresh_tokens", "partner_users", "admin_users", "partner_sessions", "partners",
    ]:
        op.drop_table(table)
    op.execute("DROP TYPE IF EXISTS partner_type_enum")
