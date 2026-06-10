"""create_monthly_closings_table

Revision ID: i3b145a829ef
Revises: h3b145a829ef
Create Date: 2026-06-09 19:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'i3b145a829ef'
down_revision: Union[str, None] = 'h3b145a829ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_NAME = "tenant_isolation"
TABLE = "monthly_closings"


def upgrade() -> None:
    op.create_table(
        TABLE,
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('competence', sa.String(length=7), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='not_started', nullable=False),
        sa.Column('score', sa.Integer(), server_default='0', nullable=False),
        sa.Column('blockers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('checklist', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('invoices_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('invoices_pending', sa.Integer(), server_default='0', nullable=False),
        sa.Column('guides_count', sa.Integer(), server_default='0', nullable=False),
        sa.Column('guides_paid', sa.Integer(), server_default='0', nullable=False),
        sa.Column('obligations_total', sa.Integer(), server_default='0', nullable=False),
        sa.Column('obligations_done', sa.Integer(), server_default='0', nullable=False),
        sa.Column('ecac_pendencies', sa.Integer(), server_default='0', nullable=False),
        sa.Column('documents_total', sa.Integer(), server_default='0', nullable=False),
        sa.Column('documents_received', sa.Integer(), server_default='0', nullable=False),
        sa.Column('dossier_generated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tenant_id', 'client_id', 'competence', name='uq_monthly_closing_client_competence'),
    )
    op.create_index('ix_monthly_closings_tenant_id', TABLE, ['tenant_id'], unique=False)
    op.create_index('ix_monthly_closings_client_id', TABLE, ['client_id'], unique=False)
    op.create_index('ix_monthly_closings_competence', TABLE, ['competence'], unique=False)

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
    op.drop_index('ix_monthly_closings_competence', table_name=TABLE)
    op.drop_index('ix_monthly_closings_client_id', table_name=TABLE)
    op.drop_index('ix_monthly_closings_tenant_id', table_name=TABLE)
    op.drop_table(TABLE)
