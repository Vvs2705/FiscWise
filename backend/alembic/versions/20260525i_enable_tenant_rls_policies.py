"""Enable PostgreSQL RLS policies for the publishable tenant table slice.

Revision ID: 20260525i
Revises: 20260525h
Create Date: 2026-05-25 19:00:00.000000

"""
from alembic import op

revision = "20260525i"
down_revision = "20260525h"
branch_labels = None
depends_on = None


POLICY_NAME = "tenant_isolation"

RLS_ENABLED_TENANT_TABLES = (
    "account_receivables",
    "accounting_clients",
    "audit_events",
    "calculator_simulations",
    "client_documents",
    "company_documents",
    "company_partners",
    "das_payments",
    "deadline_items",
    "digital_certificates",
    "fiscal_assistant_messages",
    "tax_scenarios",
)


def _quote_identifier(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def upgrade() -> None:
    for table_name in RLS_ENABLED_TENANT_TABLES:
        table = _quote_identifier(table_name)

        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table}")
        op.execute(
            f"""
            CREATE POLICY {POLICY_NAME} ON {table}
            USING (tenant_id = current_app_tenant_id())
            WITH CHECK (tenant_id = current_app_tenant_id())
            """
        )


def downgrade() -> None:
    for table_name in reversed(RLS_ENABLED_TENANT_TABLES):
        table = _quote_identifier(table_name)

        op.execute(f"DROP POLICY IF EXISTS {POLICY_NAME} ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
