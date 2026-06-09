"""create_fiscal_mailbox_table

Revision ID: h3b145a829ef
Revises: g3b145a829ef
Create Date: 2026-06-09 17:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'h3b145a829ef'
down_revision: Union[str, None] = 'g3b145a829ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_NAME = "tenant_isolation"
TABLE = "fiscal_mailbox_messages"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('external_id', sa.String(length=120), nullable=True),
        sa.Column('client_name', sa.String(length=255), nullable=True),
        sa.Column('client_cnpj', sa.String(length=18), nullable=True),
        sa.Column('subject', sa.String(length=500), nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('body', sa.Text(), nullable=True),
        sa.Column('organ', sa.String(length=50), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('deadline', sa.DateTime(timezone=True), nullable=True),
        sa.Column('risk', sa.String(length=20), server_default='none', nullable=False),
        sa.Column('status', sa.String(length=20), server_default='unread', nullable=False),
        sa.Column('task_created', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('obligation_linked', sa.String(length=120), nullable=True),
        sa.Column('tags', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fiscal_mailbox_messages_tenant_id', TABLE, ['tenant_id'], unique=False)
    op.create_index('ix_fiscal_mailbox_messages_client_id', TABLE, ['client_id'], unique=False)
    op.create_index('ix_fiscal_mailbox_messages_external_id', TABLE, ['external_id'], unique=False)
    # Idempotent ingestion: a provider message id is unique within a tenant.
    op.create_index(
        'uq_fiscal_mailbox_tenant_external',
        TABLE,
        ['tenant_id', 'external_id'],
        unique=True,
        postgresql_where=sa.text('external_id IS NOT NULL'),
    )

    op.execute(f'ALTER TABLE "{TABLE}" ENABLE ROW LEVEL SECURITY')
    op.execute(
        f"""
        CREATE POLICY {POLICY_NAME} ON "{TABLE}"
        USING (tenant_id = current_app_tenant_id())
        WITH CHECK (tenant_id = current_app_tenant_id())
        """
    )


def downgrade() -> None:
    op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{TABLE}"')
    op.execute(f'ALTER TABLE "{TABLE}" DISABLE ROW LEVEL SECURITY')
    op.drop_index('uq_fiscal_mailbox_tenant_external', table_name=TABLE)
    op.drop_index('ix_fiscal_mailbox_messages_external_id', table_name=TABLE)
    op.drop_index('ix_fiscal_mailbox_messages_client_id', table_name=TABLE)
    op.drop_index('ix_fiscal_mailbox_messages_tenant_id', table_name=TABLE)
    op.drop_table(TABLE)
