"""create_ecac_tables

Revision ID: e3b145a829ef
Revises: d3b145a829ef
Create Date: 2026-05-26 13:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'e3b145a829ef'
down_revision: Union[str, None] = 'd3b145a829ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_NAME = "tenant_isolation"
TABLES = ["ecac_proxies", "ecac_fiscal_situations"]

def upgrade() -> None:
    # 1. ecac_proxies
    op.create_table(
        'ecac_proxies',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('outorgante_cpf_cnpj', sa.String(length=14), nullable=False),
        sa.Column('outorgante_nome', sa.String(length=255), nullable=True),
        sa.Column('procurador_cpf', sa.String(length=11), nullable=False),
        sa.Column('tipo', sa.String(length=50), nullable=True),
        sa.Column('servicos_autorizados', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('data_inicio', sa.Date(), nullable=True),
        sa.Column('data_validade', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='ativa', nullable=True),
        sa.Column('ultima_verificacao', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ecac_proxies_tenant_id', 'ecac_proxies', ['tenant_id'], unique=False)
    op.create_index('ix_ecac_proxies_client_id', 'ecac_proxies', ['client_id'], unique=False)

    # 2. ecac_fiscal_situations
    op.create_table(
        'ecac_fiscal_situations',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('cpf_cnpj', sa.String(length=14), nullable=False),
        sa.Column('status_geral', sa.String(length=50), nullable=True),
        sa.Column('pendencias', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('debitos', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('certidao_status', sa.String(length=30), nullable=True),
        sa.Column('certidao_validade', sa.Date(), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('consultado_em', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ecac_fiscal_situations_tenant_id', 'ecac_fiscal_situations', ['tenant_id'], unique=False)
    op.create_index('ix_ecac_fiscal_situations_client_id', 'ecac_fiscal_situations', ['client_id'], unique=False)

    # 3. Enable RLS
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
