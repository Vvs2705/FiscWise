"""foundation user constraints

Revision ID: 20260520_user_foundation
Revises: a2f1a2feaa87
Create Date: 2026-05-20 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260520_user_foundation"
down_revision: Union[str, None] = "a2f1a2feaa87"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("full_name", sa.String(length=255), nullable=True, comment="User full name"),
    )
    op.alter_column(
        "tenants",
        "document",
        existing_type=sa.String(length=18),
        type_=sa.String(length=32),
        existing_nullable=True,
        existing_comment="CNPJ or CPF (Brazilian tax identification)",
    )
    op.create_unique_constraint("uq_users_tenant_email", "users", ["tenant_id", "email"])


def downgrade() -> None:
    op.drop_constraint("uq_users_tenant_email", "users", type_="unique")
    op.alter_column(
        "tenants",
        "document",
        existing_type=sa.String(length=32),
        type_=sa.String(length=18),
        existing_nullable=True,
        existing_comment="CNPJ or CPF (Brazilian tax identification)",
    )
    op.drop_column("users", "full_name")
