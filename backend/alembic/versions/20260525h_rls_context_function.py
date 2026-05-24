"""Add tenant context helper for PostgreSQL RLS policies.

Revision ID: 20260525h
Revises: 20260525g
Create Date: 2026-05-25 18:00:00.000000

"""
from alembic import op

revision = "20260525h"
down_revision = "20260525g"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION current_app_tenant_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        AS $$
            SELECT NULLIF(current_setting('app.current_tenant_id', true), '')::uuid
        $$;
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS current_app_tenant_id()")
