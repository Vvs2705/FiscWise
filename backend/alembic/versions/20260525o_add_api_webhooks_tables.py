"""add_api_webhooks_tables

Revision ID: 20260525o
Revises: 20260525n
Create Date: 2026-05-25 23:30:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260525o"
down_revision = "20260525n"
branch_labels = None
depends_on = None

POLICY_NAME = "tenant_isolation"


def upgrade() -> None:
    # 1. Create tenant_api_keys table
    op.create_table(
        "tenant_api_keys",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("key_hash", sa.String(length=255), nullable=False),
        sa.Column("prefix", sa.String(length=16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key_hash"),
    )
    op.create_index("idx_api_keys_tenant", "tenant_api_keys", ["tenant_id"])
    op.create_index("idx_api_keys_hash", "tenant_api_keys", ["key_hash"])

    # 2. Create webhook_subscriptions table
    op.create_table(
        "webhook_subscriptions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("secret", sa.String(length=255), nullable=False),
        sa.Column("events", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_webhook_subs_tenant", "webhook_subscriptions", ["tenant_id"])

    # 3. Create webhook_delivery_logs table
    op.create_table(
        "webhook_delivery_logs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("event", sa.String(length=255), nullable=False),
        sa.Column("url", sa.String(length=1024), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("request_body", sa.Text(), nullable=False),
        sa.Column("response_body", sa.Text(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_id"], ["webhook_subscriptions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_webhook_logs_tenant", "webhook_delivery_logs", ["tenant_id"])
    op.create_index("idx_webhook_logs_subscription", "webhook_delivery_logs", ["subscription_id"])

    # 4. Enable RLS on all three tables
    for table in ("tenant_api_keys", "webhook_subscriptions", "webhook_delivery_logs"):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = '{table}') THEN
                    ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY;
                    DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";
                    CREATE POLICY {POLICY_NAME} ON "{table}"
                      USING (tenant_id = current_app_tenant_id())
                      WITH CHECK (tenant_id = current_app_tenant_id());
                END IF;
            END $$;
            """
        )


def downgrade() -> None:
    # 1. Disable RLS and drop policies
    for table in ("webhook_delivery_logs", "webhook_subscriptions", "tenant_api_keys"):
        op.execute(
            f"""
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = '{table}') THEN
                    DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}";
                    ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY;
                END IF;
            END $$;
            """
        )

    # 2. Drop indexes and tables in reverse order
    op.drop_index("idx_webhook_logs_subscription", table_name="webhook_delivery_logs")
    op.drop_index("idx_webhook_logs_tenant", table_name="webhook_delivery_logs")
    op.drop_table("webhook_delivery_logs")

    op.drop_index("idx_webhook_subs_tenant", table_name="webhook_subscriptions")
    op.drop_table("webhook_subscriptions")

    op.drop_index("idx_api_keys_hash", table_name="tenant_api_keys")
    op.drop_index("idx_api_keys_tenant", table_name="tenant_api_keys")
    op.drop_table("tenant_api_keys")
