"""add client_code to accounting_clients

Revision ID: 20260521_client_code
Revises: 20260520_fix_enum_case
Create Date: 2026-05-21 00:00:00.000000

Adds a 4-digit zero-padded code that is unique per tenant (not globally),
used to identify clients with a short human-readable code.

Steps:
  1. Add column client_code VARCHAR(4) nullable (so existing rows survive)
  2. Back-fill existing rows with a random 4-digit code using PostgreSQL arithmetic
  3. Enforce NOT NULL
  4. Create unique index on (tenant_id, client_code)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_client_code"
down_revision: Union[str, None] = "20260520_fix_enum_case"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Step 1: add column nullable so existing rows don't violate NOT NULL yet
    op.add_column(
        "accounting_clients",
        sa.Column("client_code", sa.String(4), nullable=True, server_default=""),
    )

    # Step 2: back-fill existing rows with a random 4-digit code (zero-padded).
    # lpad(floor(random()*10000)::int::text, 4, '0') produces values in
    # ['0000'..'9999'].  Collisions are acceptable here: the application layer
    # enforces uniqueness per tenant on creation; this migration only needs to
    # produce *some* non-null value so the NOT NULL constraint can be applied.
    op.execute(
        sa.text(
            "UPDATE accounting_clients "
            "SET client_code = lpad(floor(random() * 10000)::int::text, 4, '0') "
            "WHERE client_code IS NULL OR client_code = ''"
        )
    )

    # Step 3: enforce NOT NULL now that every row has a value
    op.alter_column("accounting_clients", "client_code", nullable=False, server_default=None)

    # Step 4: unique index per tenant (not globally)
    op.create_index(
        "ix_accounting_clients_tenant_client_code",
        "accounting_clients",
        ["tenant_id", "client_code"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_accounting_clients_tenant_client_code",
        table_name="accounting_clients",
    )
    op.drop_column("accounting_clients", "client_code")
