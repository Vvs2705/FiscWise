"""Add audit logs table and composite indexes

Revision ID: 20260524c
Revises: 20260524b
Create Date: 2026-05-24 13:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260524c'
down_revision = '20260524b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create audit_events table
    op.create_table(
        'audit_events',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_user_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('actor_role', sa.String(length=50), nullable=True),
        sa.Column('action', sa.String(length=100), nullable=False),
        sa.Column('entity_type', sa.String(length=50), nullable=False),
        sa.Column('entity_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('before_data', sa.JSON(), nullable=True),
        sa.Column('after_data', sa.JSON(), nullable=True),
        sa.Column('ip_address', sa.String(length=45), nullable=True),
        sa.Column('user_agent', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['actor_user_id'], ['users.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create default indexes for audit_events
    op.create_index(op.f('ix_audit_events_tenant_id'), 'audit_events', ['tenant_id'], unique=False)
    op.create_index(op.f('ix_audit_events_actor_user_id'), 'audit_events', ['actor_user_id'], unique=False)
    op.create_index(op.f('ix_audit_events_action'), 'audit_events', ['action'], unique=False)
    op.create_index(op.f('ix_audit_events_entity_type'), 'audit_events', ['entity_type'], unique=False)
    op.create_index(op.f('ix_audit_events_entity_id'), 'audit_events', ['entity_id'], unique=False)
    op.create_index(op.f('ix_audit_events_created_at'), 'audit_events', ['created_at'], unique=False)

    # Create composite indexes
    op.create_index('idx_clients_tenant_status', 'accounting_clients', ['tenant_id', 'status'], unique=False)
    op.create_index('idx_deadlines_tenant_due_status', 'deadline_items', ['tenant_id', 'due_date', 'status'], unique=False)
    op.create_index('idx_documents_tenant_client_created', 'client_documents', ['tenant_id', 'client_id', 'created_at'], unique=False)
    op.create_index('idx_das_tenant_client_period', 'das_payments', ['tenant_id', 'client_id', 'period'], unique=False)
    op.create_index('idx_receivables_tenant_due_status', 'account_receivables', ['tenant_id', 'due_date', 'status'], unique=False)


def downgrade() -> None:
    # Drop composite indexes
    op.drop_index('idx_receivables_tenant_due_status', table_name='account_receivables')
    op.drop_index('idx_das_tenant_client_period', table_name='das_payments')
    op.drop_index('idx_documents_tenant_client_created', table_name='client_documents')
    op.drop_index('idx_deadlines_tenant_due_status', table_name='deadline_items')
    op.drop_index('idx_clients_tenant_status', table_name='accounting_clients')

    # Drop audit_events table (it drops default indexes automatically)
    op.drop_table('audit_events')
