"""create_guias_tables

Revision ID: f3b145a829ef
Revises: e3b145a829ef
Create Date: 2026-05-26 14:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'f3b145a829ef'
down_revision: Union[str, None] = 'e3b145a829ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_NAME = "tenant_isolation"
TABLES = ["tax_guides"]

def upgrade() -> None:
    op.create_table(
        'tax_guides',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('tipo', sa.String(length=20), nullable=False),  # 'DAS' | 'DARF' | 'GPS' | 'ISS' | 'outro'
        sa.Column('competencia', sa.Date(), nullable=False),
        sa.Column('valor', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('vencimento', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pendente', nullable=False),  # 'pendente' | 'enviada' | 'paga' | 'atrasada'
        sa.Column('pdf_storage_path', sa.String(length=500), nullable=True),
        sa.Column('comprovante_storage_path', sa.String(length=500), nullable=True),
        sa.Column('enviada_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('paga_em', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tax_guides_tenant_id', 'tax_guides', ['tenant_id'], unique=False)
    op.create_index('ix_tax_guides_client_id', 'tax_guides', ['client_id'], unique=False)
    op.create_index('ix_tax_guides_status', 'tax_guides', ['status'], unique=False)

    # Enable RLS
    for table in TABLES:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(
            f"""
            CREATE POLICY {POLICY_NAME} ON "{table}"
            USING (tenant_id = current_app_tenant_id())
            WITH CHECK (tenant_id = current_app_tenant_id())
            """
        )

def downgrade() -> None:
    for table in reversed(TABLES):
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
        op.drop_table(table)
