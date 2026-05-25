"""add_fiscal_monitor_tables

Revision ID: 20260525m
Revises: 20260525l
Create Date: 2026-05-25 22:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260525m"
down_revision = "20260525l"
branch_labels = None
depends_on = None

POLICY_NAME = "tenant_isolation"


def upgrade() -> None:
    # 1. Create fiscal_monitor_summaries table
    op.create_table(
        "fiscal_monitor_summaries",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("last_sync_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cnpj_status", sa.String(length=50), nullable=True, server_default="REGULAR"),
        sa.Column("situation_details", sa.JSON(), nullable=True),
        sa.Column("has_debts", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("debt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_debt_value", sa.Numeric(precision=12, scale=2), nullable=False, server_default="0.00"),
        sa.Column("debts_list", sa.JSON(), nullable=True),
        sa.Column("cnd_status", sa.String(length=50), nullable=True, server_default="REGULAR"),
        sa.Column("last_cnd_download_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_cnd_document_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["accounting_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["last_cnd_document_id"], ["client_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create fiscal_nfes table
    op.create_table(
        "fiscal_nfes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("access_key", sa.String(length=44), nullable=False),
        sa.Column("nfe_number", sa.String(length=20), nullable=False),
        sa.Column("nfe_type", sa.String(length=16), nullable=False),
        sa.Column("issuer_name", sa.String(length=255), nullable=False),
        sa.Column("issuer_document", sa.String(length=32), nullable=False),
        sa.Column("recipient_name", sa.String(length=255), nullable=False),
        sa.Column("recipient_document", sa.String(length=32), nullable=False),
        sa.Column("value", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("retrieved_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("xml_url", sa.String(length=1024), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="AUTORIZADA"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["accounting_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create indexes
    op.create_index(
        "idx_fiscal_monitor_tenant_client",
        "fiscal_monitor_summaries",
        ["tenant_id", "client_id"],
        unique=True,
    )
    op.create_index(
        "idx_fiscal_nfes_tenant_client_issued",
        "fiscal_nfes",
        ["tenant_id", "client_id", "issued_at"],
    )
    op.create_index(
        "idx_fiscal_nfes_access_key",
        "fiscal_nfes",
        ["access_key"],
        unique=True,
    )

    # 4. Enable RLS and create isolation policies on PostgreSQL
    op.execute(
        f"""
        DO $$
        BEGIN
            -- Policy for fiscal_monitor_summaries
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'fiscal_monitor_summaries') THEN
                ALTER TABLE "fiscal_monitor_summaries" ENABLE ROW LEVEL SECURITY;
                DROP POLICY IF EXISTS {POLICY_NAME} ON "fiscal_monitor_summaries";
                CREATE POLICY {POLICY_NAME} ON "fiscal_monitor_summaries"
                  USING (tenant_id = current_app_tenant_id())
                  WITH CHECK (tenant_id = current_app_tenant_id());
            END IF;

            -- Policy for fiscal_nfes
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'fiscal_nfes') THEN
                ALTER TABLE "fiscal_nfes" ENABLE ROW LEVEL SECURITY;
                DROP POLICY IF EXISTS {POLICY_NAME} ON "fiscal_nfes";
                CREATE POLICY {POLICY_NAME} ON "fiscal_nfes"
                  USING (tenant_id = current_app_tenant_id())
                  WITH CHECK (tenant_id = current_app_tenant_id());
            END IF;
        END $$;
        """
    )


def downgrade() -> None:
    # 1. Disable RLS and drop policies
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'fiscal_nfes') THEN
                DROP POLICY IF EXISTS {POLICY_NAME} ON "fiscal_nfes";
                ALTER TABLE "fiscal_nfes" DISABLE ROW LEVEL SECURITY;
            END IF;

            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'fiscal_monitor_summaries') THEN
                DROP POLICY IF EXISTS {POLICY_NAME} ON "fiscal_monitor_summaries";
                ALTER TABLE "fiscal_monitor_summaries" DISABLE ROW LEVEL SECURITY;
            END IF;
        END $$;
        """
    )

    # 2. Drop indexes
    op.drop_index("idx_fiscal_nfes_access_key", table_name="fiscal_nfes")
    op.drop_index("idx_fiscal_nfes_tenant_client_issued", table_name="fiscal_nfes")
    op.drop_index("idx_fiscal_monitor_tenant_client", table_name="fiscal_monitor_summaries")

    # 3. Drop tables
    op.drop_table("fiscal_nfes")
    op.drop_table("fiscal_monitor_summaries")
