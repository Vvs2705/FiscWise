"""create_nfse_tables

Revision ID: 6b7b8687843d
Revises: 20260526a
Create Date: 2026-05-26 08:50:51.874064

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '6b7b8687843d'
down_revision: Union[str, None] = '20260526a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_NAME = "tenant_isolation"
TABLES = ["invoice_issuers", "invoices", "invoice_events", "invoice_rejections"]

def upgrade() -> None:
    # 1. invoice_issuers
    op.create_table(
        'invoice_issuers',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('cnpj', sa.String(length=14), nullable=False),
        sa.Column('inscricao_municipal', sa.String(length=50), nullable=True),
        sa.Column('regime_tributario', sa.String(length=20), nullable=False),
        sa.Column('municipio_ibge', sa.String(length=7), nullable=False),
        sa.Column('cod_servico_lc116', sa.String(length=10), nullable=True),
        sa.Column('aliquota_iss', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('retencao_iss', sa.Boolean(), server_default='false', nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoice_issuers_tenant_id', 'invoice_issuers', ['tenant_id'], unique=False)
    op.create_index('ix_invoice_issuers_client_id', 'invoice_issuers', ['client_id'], unique=False)

    # 2. invoices
    op.create_table(
        'invoices',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('issuer_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('status', sa.String(length=20), server_default='draft', nullable=False),
        sa.Column('numero', sa.String(length=50), nullable=True),
        sa.Column('serie', sa.String(length=5), nullable=True),
        sa.Column('competencia', sa.Date(), nullable=False),
        sa.Column('valor_servico', sa.Numeric(precision=15, scale=2), nullable=False),
        sa.Column('valor_deducoes', sa.Numeric(precision=15, scale=2), server_default='0', nullable=True),
        sa.Column('valor_iss', sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column('descricao_servico', sa.Text(), nullable=False),
        sa.Column('tomador_nome', sa.String(length=255), nullable=True),
        sa.Column('tomador_cpf_cnpj', sa.String(length=14), nullable=True),
        sa.Column('tomador_email', sa.String(length=255), nullable=True),
        sa.Column('tomador_municipio_ibge', sa.String(length=7), nullable=True),
        sa.Column('provider_protocol', sa.String(length=100), nullable=True),
        sa.Column('provider_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('xml_content', sa.Text(), nullable=True),
        sa.Column('pdf_storage_path', sa.String(length=500), nullable=True),
        sa.Column('xml_storage_path', sa.String(length=500), nullable=True),
        sa.Column('billing_charge_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['issuer_id'], ['invoice_issuers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoices_tenant_id', 'invoices', ['tenant_id'], unique=False)
    op.create_index('ix_invoices_issuer_id', 'invoices', ['issuer_id'], unique=False)
    op.create_index('ix_invoices_client_id', 'invoices', ['client_id'], unique=False)
    op.create_index('ix_invoices_status', 'invoices', ['status'], unique=False)

    # 3. invoice_events
    op.create_table(
        'invoice_events',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('invoice_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoice_events_tenant_id', 'invoice_events', ['tenant_id'], unique=False)
    op.create_index('ix_invoice_events_invoice_id', 'invoice_events', ['invoice_id'], unique=False)

    # 4. invoice_rejections
    op.create_table(
        'invoice_rejections',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False, server_default=sa.text('gen_random_uuid()')),
        sa.Column('invoice_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('codigo_rejeicao', sa.String(length=20), nullable=True),
        sa.Column('descricao', sa.Text(), nullable=False),
        sa.Column('raw_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=True),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_invoice_rejections_tenant_id', 'invoice_rejections', ['tenant_id'], unique=False)
    op.create_index('ix_invoice_rejections_invoice_id', 'invoice_rejections', ['invoice_id'], unique=False)

    # 5. Enable RLS and create isolation policy for each table
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
