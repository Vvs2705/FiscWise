"""add_rag_documents_table

Revision ID: 20260525n
Revises: 20260525m
Create Date: 2026-05-25 23:00:00.000000

"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260525n"
down_revision = "20260525m"
branch_labels = None
depends_on = None

POLICY_NAME = "tenant_isolation"


def upgrade() -> None:
    # 1. Create rag_documents table
    op.create_table(
        "rag_documents",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False, server_default="Procedimento Interno"),
        sa.Column("category", sa.String(length=50), nullable=False, server_default="procedimento"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create indexes
    op.create_index(
        "idx_rag_documents_tenant_title",
        "rag_documents",
        ["tenant_id", "title"],
    )
    op.create_index(
        "idx_rag_documents_tenant_category",
        "rag_documents",
        ["tenant_id", "category"],
    )

    # 3. Enable RLS and create isolation policies on PostgreSQL
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'rag_documents') THEN
                ALTER TABLE "rag_documents" ENABLE ROW LEVEL SECURITY;
                DROP POLICY IF EXISTS {POLICY_NAME} ON "rag_documents";
                CREATE POLICY {POLICY_NAME} ON "rag_documents"
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
            IF EXISTS (SELECT 1 FROM pg_tables WHERE tablename = 'rag_documents') THEN
                DROP POLICY IF EXISTS {POLICY_NAME} ON "rag_documents";
                ALTER TABLE "rag_documents" DISABLE ROW LEVEL SECURITY;
            END IF;
        END $$;
        """
    )

    # 2. Drop indexes
    op.drop_index("idx_rag_documents_tenant_category", table_name="rag_documents")
    op.drop_index("idx_rag_documents_tenant_title", table_name="rag_documents")

    # 3. Drop table
    op.drop_table("rag_documents")
