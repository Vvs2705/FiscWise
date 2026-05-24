"""Add monthly das payments table

Revision ID: 20260524b
Revises: 20260524
Create Date: 2026-05-24 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20260524b'
down_revision = '20260524'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create das_payments table
    op.create_table(
        'das_payments',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('period', sa.String(length=7), nullable=False),
        sa.Column('revenue', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=32), nullable=False),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('file_url', sa.String(length=1024), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Create indexes
    op.create_index(
        op.f('ix_das_payments_client_id'),
        'das_payments',
        ['client_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_das_payments_due_date'),
        'das_payments',
        ['due_date'],
        unique=False
    )
    op.create_index(
        op.f('ix_das_payments_period'),
        'das_payments',
        ['period'],
        unique=False
    )
    op.create_index(
        op.f('ix_das_payments_status'),
        'das_payments',
        ['status'],
        unique=False
    )
    op.create_index(
        op.f('ix_das_payments_tenant_id'),
        'das_payments',
        ['tenant_id'],
        unique=False
    )


def downgrade() -> None:
    # Drop indexes
    op.drop_index(op.f('ix_das_payments_tenant_id'), table_name='das_payments')
    op.drop_index(op.f('ix_das_payments_status'), table_name='das_payments')
    op.drop_index(op.f('ix_das_payments_period'), table_name='das_payments')
    op.drop_index(op.f('ix_das_payments_due_date'), table_name='das_payments')
    op.drop_index(op.f('ix_das_payments_client_id'), table_name='das_payments')

    # Drop table
    op.drop_table('das_payments')
