"""RLS policies for all fiscal core domain tables

Revision ID: 20260526d
Revises: 20260526c
Create Date: 2026-05-26 15:00:00.000000

Enables Row-Level Security on all fiscal core domain tables so that
each tenant can only access its own rows via the set_tenant_id() RLS function.
"""
from alembic import op

revision = '20260526d'
down_revision = '20260526c'
branch_labels = None
depends_on = None

# Tables added in 20260526c that need tenant RLS
# NOTE: digital_certificates already has RLS from 20260525i — excluded here
_TABLES = [
    'invoice_issuers',
    'invoice_service_profiles',
    'invoices',
    'invoice_events',
    'fiscal_subjects',
    'ecac_credentials',
    'ecac_requests',
    'tax_status_snapshots',
    'certificate_usage_events',
    'powers_of_attorney',
    'fiscal_guides',
    'fiscal_guide_events',
    'fiscal_mailbox_messages',
    'monthly_closings',
    'monthly_closing_items',
    'fiscal_dossiers',
]


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY;")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {table}
            USING (tenant_id = current_setting('app.tenant_id', true)::uuid);
            """
        )


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {table};")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY;")
