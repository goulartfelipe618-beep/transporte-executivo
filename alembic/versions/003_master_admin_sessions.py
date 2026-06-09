"""master_admin_sessions web

Revision ID: 003
Revises: 002
Create Date: 2026-06-08

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "master_admin_sessions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("admin_id", sa.String(64), nullable=False),
        sa.Column("admin_email", sa.String(255), nullable=False),
        sa.Column("admin_nome", sa.String(255), server_default=""),
        sa.Column("admin_perfil", sa.String(128), server_default=""),
        sa.Column("ip_address", sa.String(45)),
        sa.Column("user_agent", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_master_admin_sessions_admin_id", "master_admin_sessions", ["admin_id"])
    op.create_index("ix_master_admin_sessions_expires_at", "master_admin_sessions", ["expires_at"])


def downgrade() -> None:
    op.drop_index("ix_master_admin_sessions_expires_at", table_name="master_admin_sessions")
    op.drop_index("ix_master_admin_sessions_admin_id", table_name="master_admin_sessions")
    op.drop_table("master_admin_sessions")
