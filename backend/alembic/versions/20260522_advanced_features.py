"""add advanced features schema

Revision ID: 20260522
Revises: 20260521b
Create Date: 2026-05-22 00:00:00.000000

Adds fields for:
  - Advanced client filtering (cnae_code, index tax_regime, index entity_type)
  - Automated billing (monthly_fee, billing_day, portal_user_id)
  - Document parsing (parse_status, parsed_data, parse_error, parsed_at)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20260522"
down_revision = "20260521b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # accounting_clients table changes
    op.add_column(
        "accounting_clients",
        sa.Column("cnae_code", sa.String(20), nullable=True),
    )
    op.add_column(
        "accounting_clients",
        sa.Column("monthly_fee", sa.Numeric(10, 2), nullable=True),
    )
    op.add_column(
        "accounting_clients",
        sa.Column("billing_day", sa.Integer(), nullable=False, server_default="1"),
    )
    op.add_column(
        "accounting_clients",
        sa.Column("portal_user_id", sa.UUID(), nullable=True),
    )

    # Create indexes
    op.create_index("ix_accounting_clients_cnae_code", "accounting_clients", ["cnae_code"])
    op.create_index("ix_accounting_clients_tax_regime", "accounting_clients", ["tax_regime"])
    op.create_index("ix_accounting_clients_entity_type", "accounting_clients", ["entity_type"])
    op.create_index("ix_accounting_clients_portal_user_id", "accounting_clients", ["portal_user_id"])

    # client_documents table changes
    op.add_column(
        "client_documents",
        sa.Column("parse_status", sa.String(32), nullable=False, server_default="pending"),
    )
    op.add_column(
        "client_documents",
        sa.Column("parsed_data", postgresql.JSON(astext_type=sa.Text()), nullable=True),
    )
    op.add_column(
        "client_documents",
        sa.Column("parse_error", sa.Text(), nullable=True),
    )
    op.add_column(
        "client_documents",
        sa.Column("parsed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    # client_documents table rollback
    op.drop_column("client_documents", "parsed_at")
    op.drop_column("client_documents", "parse_error")
    op.drop_column("client_documents", "parsed_data")
    op.drop_column("client_documents", "parse_status")

    # accounting_clients table rollback
    op.drop_index("ix_accounting_clients_portal_user_id", table_name="accounting_clients")
    op.drop_index("ix_accounting_clients_entity_type", table_name="accounting_clients")
    op.drop_index("ix_accounting_clients_tax_regime", table_name="accounting_clients")
    op.drop_index("ix_accounting_clients_cnae_code", table_name="accounting_clients")

    op.drop_column("accounting_clients", "portal_user_id")
    op.drop_column("accounting_clients", "billing_day")
    op.drop_column("accounting_clients", "monthly_fee")
    op.drop_column("accounting_clients", "cnae_code")
