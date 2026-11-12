"""Sync offline-first (Frente G): version + cursor do pull, sync_devices/events/conflicts.

Contrato em docs/arquitetura/OFFLINE_SYNC.md, seção 4.2. Tabelas novas com RLS
tenant_isolation (current_app_tenant_id()), igual às demais tabelas de escritório.

Revision ID: o1i7bc49gk6
Revises: o0a1b2c3d4e5
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "o1i7bc49gk6"
down_revision = "o0a1b2c3d4e5"
branch_labels = None
depends_on = None

POLICY_NAME = "tenant_isolation"

# tabela -> nome do índice do cursor (tenant_id, updated_at, id)
VERSIONED_TABLES = {
    "accounting_clients": "idx_clients_tenant_updated_id",
    "deadline_items": "idx_deadlines_tenant_updated_id",
    "digital_certificates": "idx_certificates_tenant_updated_id",
    "account_receivables": "idx_receivables_tenant_updated_id",
}
INVOICE_CURSOR_INDEX = "idx_invoices_tenant_updated_id"
SYNC_TABLES = ("sync_devices", "sync_events", "sync_conflicts")


def _enable_rls(table: str) -> None:
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
    op.execute(
        f"""
        CREATE POLICY {POLICY_NAME} ON "{table}"
        USING (tenant_id = current_app_tenant_id())
        WITH CHECK (tenant_id = current_app_tenant_id())
        """
    )


def upgrade() -> None:
    for table, index in VERSIONED_TABLES.items():
        op.add_column(table, sa.Column("version", sa.Integer(), nullable=False, server_default="1"))
        op.create_index(index, table, ["tenant_id", "updated_at", "id"])
    op.create_index(INVOICE_CURSOR_INDEX, "invoices", ["tenant_id", "updated_at", "id"])

    op.create_table(
        "sync_devices",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("platform", sa.Text(), nullable=False),
        sa.Column("app_version", sa.Text(), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sync_devices_tenant_id", "sync_devices", ["tenant_id"])
    op.create_index("ix_sync_devices_user_id", "sync_devices", ["user_id"])

    op.create_table(
        "sync_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("sequence", sa.BigInteger(), sa.Identity(always=False), nullable=False, unique=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("device_id", sa.UUID(as_uuid=True), sa.ForeignKey("sync_devices.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False, unique=True),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("operation", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("client_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint("status IN ('applied', 'rejected')", name="ck_sync_events_status"),
    )
    op.create_index("idx_sync_events_tenant_sequence", "sync_events", ["tenant_id", "sequence"])
    op.create_index("idx_sync_events_tenant_entity", "sync_events", ["tenant_id", "entity_type", "entity_id"])
    op.create_index("idx_sync_events_received_at", "sync_events", ["received_at"])

    op.create_table(
        "sync_conflicts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("tenant_id", sa.UUID(as_uuid=True), sa.ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False),
        sa.Column("entity_type", sa.Text(), nullable=False),
        sa.Column("entity_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("event_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("device_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("base_version", sa.Integer(), nullable=True),
        sa.Column("server_version", sa.Integer(), nullable=False),
        sa.Column("fields_overwritten", postgresql.JSONB(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_by", sa.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("idx_sync_conflicts_tenant_resolved", "sync_conflicts", ["tenant_id", "resolved_at"])
    op.create_index("idx_sync_conflicts_tenant_event", "sync_conflicts", ["tenant_id", "event_id"])

    for table in SYNC_TABLES:
        _enable_rls(table)


def downgrade() -> None:
    for table in reversed(SYNC_TABLES):
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')

    op.drop_index("idx_sync_conflicts_tenant_event", table_name="sync_conflicts")
    op.drop_index("idx_sync_conflicts_tenant_resolved", table_name="sync_conflicts")
    op.drop_table("sync_conflicts")

    op.drop_index("idx_sync_events_received_at", table_name="sync_events")
    op.drop_index("idx_sync_events_tenant_entity", table_name="sync_events")
    op.drop_index("idx_sync_events_tenant_sequence", table_name="sync_events")
    op.drop_table("sync_events")

    op.drop_index("ix_sync_devices_user_id", table_name="sync_devices")
    op.drop_index("ix_sync_devices_tenant_id", table_name="sync_devices")
    op.drop_table("sync_devices")

    op.drop_index(INVOICE_CURSOR_INDEX, table_name="invoices")
    for table, index in reversed(list(VERSIONED_TABLES.items())):
        op.drop_index(index, table_name=table)
        op.drop_column(table, "version")
