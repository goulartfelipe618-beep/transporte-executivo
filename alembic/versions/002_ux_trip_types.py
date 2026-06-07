"""UX fields: trip types, hourly, vehicle details, passenger extras

Revision ID: 002
Revises: 001
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("booking_reservations", sa.Column("trip_type", sa.String(32), server_default="one_way"))
    op.add_column("booking_reservations", sa.Column("city", sa.String(255), nullable=True))
    op.add_column("booking_reservations", sa.Column("hourly_hours", sa.Integer(), nullable=True))
    op.add_column("booking_reservations", sa.Column("search_notes", sa.Text(), nullable=True))
    op.add_column("booking_reservations", sa.Column("distance_km", sa.Numeric(8, 2), nullable=True))
    op.add_column("booking_reservations", sa.Column("duration_minutes", sa.Integer(), nullable=True))
    op.add_column("booking_reservations", sa.Column("vehicle_brand", sa.String(64), nullable=True))
    op.add_column("booking_reservations", sa.Column("vehicle_model", sa.String(128), nullable=True))
    op.add_column("booking_reservations", sa.Column("taxes_amount", sa.Numeric(12, 2), nullable=True))

    op.add_column("booking_passengers", sa.Column("whatsapp", sa.String(32), nullable=True))
    op.add_column("booking_passengers", sa.Column("company", sa.String(255), nullable=True))
    op.add_column("booking_passengers", sa.Column("flight_number", sa.String(32), nullable=True))
    op.add_column("booking_passengers", sa.Column("lgpd_accepted", sa.Boolean(), server_default="false"))


def downgrade() -> None:
    for col in [
        "trip_type", "city", "hourly_hours", "search_notes", "distance_km",
        "duration_minutes", "vehicle_brand", "vehicle_model", "taxes_amount",
    ]:
        op.drop_column("booking_reservations", col)
    for col in ["whatsapp", "company", "flight_number", "lgpd_accepted"]:
        op.drop_column("booking_passengers", col)
