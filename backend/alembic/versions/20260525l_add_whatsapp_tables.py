"""add_whatsapp_tables

Revision ID: 20260525l
Revises: 20260525k
Create Date: 2026-05-25 21:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260525l"
down_revision = "20260525k"
branch_labels = None
depends_on = None

POLICY_NAME = "tenant_isolation"


def upgrade() -> None:
    # 1. Create whatsapp_inboxes table
    op.create_table(
        "whatsapp_inboxes",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("client_id", sa.UUID(), nullable=True),
        sa.Column("phone_number", sa.String(length=40), nullable=False),
        sa.Column("customer_name", sa.String(length=255), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_message_preview", sa.Text(), nullable=True),
        sa.Column("unread_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["client_id"], ["accounting_clients.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create whatsapp_messages table
    op.create_table(
        "whatsapp_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("inbox_id", sa.UUID(), nullable=False),
        sa.Column("direction", sa.String(length=20), nullable=False),
        sa.Column("sender_name", sa.String(length=255), nullable=True),
        sa.Column("sender_phone", sa.String(length=40), nullable=True),
        sa.Column("message_type", sa.String(length=20), nullable=False, server_default="text"),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("media_url", sa.String(length=1024), nullable=True),
        sa.Column("external_message_id", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="sent"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["inbox_id"], ["whatsapp_inboxes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 3. Create indexes
    op.create_index(
        "idx_whatsapp_inboxes_tenant_phone",
        "whatsapp_inboxes",
        ["tenant_id", "phone_number"],
        unique=True,
    )
    op.create_index(
        "idx_whatsapp_inboxes_tenant_client",
        "whatsapp_inboxes",
        ["tenant_id", "client_id"],
    )
    op.create_index(
        "idx_whatsapp_messages_inbox_created",
        "whatsapp_messages",
        ["inbox_id", "created_at"],
    )
    op.create_index(
        "idx_whatsapp_messages_external_id",
        "whatsapp_messages",
        ["external_message_id"],
    )

    # 4. Enable RLS and create isolation policies on PostgreSQL
    # Using execute with raw SQL, guarded so it won't break if run on SQLite (e.g. testing)
    op.execute(
        f"""
        DO $$
        BEGIN
            -- Policy for whatsapp_inboxes
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'whatsapp_inboxes') THEN
                ALTER TABLE "whatsapp_inboxes" ENABLE ROW LEVEL SECURITY;
                DROP POLICY IF EXISTS {POLICY_NAME} ON "whatsapp_inboxes";
                CREATE POLICY {POLICY_NAME} ON "whatsapp_inboxes"
                  USING (tenant_id = current_app_tenant_id())
                  WITH CHECK (tenant_id = current_app_tenant_id());
            END IF;

            -- Policy for whatsapp_messages
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'whatsapp_messages') THEN
                ALTER TABLE "whatsapp_messages" ENABLE ROW LEVEL SECURITY;
                DROP POLICY IF EXISTS {POLICY_NAME} ON "whatsapp_messages";
                CREATE POLICY {POLICY_NAME} ON "whatsapp_messages"
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
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'whatsapp_messages') THEN
                DROP POLICY IF EXISTS {POLICY_NAME} ON "whatsapp_messages";
                ALTER TABLE "whatsapp_messages" DISABLE ROW LEVEL SECURITY;
            END IF;

            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'whatsapp_inboxes') THEN
                DROP POLICY IF EXISTS {POLICY_NAME} ON "whatsapp_inboxes";
                ALTER TABLE "whatsapp_inboxes" DISABLE ROW LEVEL SECURITY;
            END IF;
        END $$;
        """
    )

    # 2. Drop indexes
    op.drop_index("idx_whatsapp_messages_external_id", table_name="whatsapp_messages")
    op.drop_index("idx_whatsapp_messages_inbox_created", table_name="whatsapp_messages")
    op.drop_index("idx_whatsapp_inboxes_tenant_client", table_name="whatsapp_inboxes")
    op.drop_index("idx_whatsapp_inboxes_tenant_phone", table_name="whatsapp_inboxes")

    # 3. Drop tables
    op.drop_table("whatsapp_messages")
    op.drop_table("whatsapp_inboxes")
