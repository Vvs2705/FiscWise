"""add profile fields to users and tenants

Revision ID: 20260521b
Revises: 20260521_client_code
Create Date: 2026-05-21 00:00:00.000000

Adds optional profile/contact fields:
  - users.phone VARCHAR(20)
  - tenants.plan_slug VARCHAR(50)
  - tenants.phone VARCHAR(20)
  - tenants.address VARCHAR(500)
  - tenants.website VARCHAR(255)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521b"
down_revision: Union[str, None] = "20260521_client_code"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("phone", sa.String(20), nullable=True),
    )

    op.add_column(
        "tenants",
        sa.Column("plan_slug", sa.String(50), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("phone", sa.String(20), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("address", sa.String(500), nullable=True),
    )
    op.add_column(
        "tenants",
        sa.Column("website", sa.String(255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("tenants", "website")
    op.drop_column("tenants", "address")
    op.drop_column("tenants", "phone")
    op.drop_column("tenants", "plan_slug")
    op.drop_column("users", "phone")
