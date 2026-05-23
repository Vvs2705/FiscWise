"""Expanded client registry with responsible person and company documents

Revision ID: 20260524_expanded_client_registry
Revises: 20260523_client_portal_invites
Create Date: 2026-05-24 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260524'
down_revision = '20260523'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create company_document_type_enum
    company_document_type_enum = postgresql.ENUM(
        'cnpj',
        'contrato_social',
        'inscricao_municipal',
        'inscricao_estadual',
        'alvara_funcionamento',
        'licenca_sanitaria',
        'cnes',
        'alvara_bombeiros',
        'cro_juridico',
        name='company_document_type_enum',
        create_type=True
    )
    company_document_type_enum.create(op.get_bind())

    # Add columns to accounting_clients table
    op.add_column(
        'accounting_clients',
        sa.Column('responsible_name', sa.String(255), nullable=True)
    )
    op.add_column(
        'accounting_clients',
        sa.Column('responsible_cpf', sa.String(20), nullable=True)
    )
    op.add_column(
        'accounting_clients',
        sa.Column('responsible_address', sa.String(255), nullable=True)
    )
    op.add_column(
        'accounting_clients',
        sa.Column('responsible_phone', sa.String(40), nullable=True)
    )
    op.add_column(
        'accounting_clients',
        sa.Column('responsible_email', sa.String(255), nullable=True)
    )

    # Create index on responsible_cpf
    op.create_index(
        op.f('ix_accounting_clients_responsible_cpf'),
        'accounting_clients',
        ['responsible_cpf'],
        unique=False
    )

    # Create company_partners table
    op.create_table(
        'company_partners',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('cpf', sa.String(20), nullable=False),
        sa.Column('participation_percentage', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('entry_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        op.f('ix_company_partners_client_id'),
        'company_partners',
        ['client_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_company_partners_cpf'),
        'company_partners',
        ['cpf'],
        unique=False
    )
    op.create_index(
        op.f('ix_company_partners_status'),
        'company_partners',
        ['status'],
        unique=False
    )
    op.create_index(
        op.f('ix_company_partners_tenant_id'),
        'company_partners',
        ['tenant_id'],
        unique=False
    )

    # Create company_documents table
    op.create_table(
        'company_documents',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('document_type', sa.Enum('cnpj', 'contrato_social', 'inscricao_municipal', 'inscricao_estadual', 'alvara_funcionamento', 'licenca_sanitaria', 'cnes', 'alvara_bombeiros', 'cro_juridico', name='company_document_type_enum'), nullable=False),
        sa.Column('file_url', sa.String(1024), nullable=False),
        sa.Column('upload_date', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('expiration_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    op.create_index(
        op.f('ix_company_documents_client_id'),
        'company_documents',
        ['client_id'],
        unique=False
    )
    op.create_index(
        op.f('ix_company_documents_document_type'),
        'company_documents',
        ['document_type'],
        unique=False
    )
    op.create_index(
        op.f('ix_company_documents_expiration_date'),
        'company_documents',
        ['expiration_date'],
        unique=False
    )
    op.create_index(
        op.f('ix_company_documents_status'),
        'company_documents',
        ['status'],
        unique=False
    )
    op.create_index(
        op.f('ix_company_documents_tenant_id'),
        'company_documents',
        ['tenant_id'],
        unique=False
    )


def downgrade() -> None:
    # Drop company_documents table
    op.drop_index(
        op.f('ix_company_documents_tenant_id'),
        table_name='company_documents'
    )
    op.drop_index(
        op.f('ix_company_documents_status'),
        table_name='company_documents'
    )
    op.drop_index(
        op.f('ix_company_documents_expiration_date'),
        table_name='company_documents'
    )
    op.drop_index(
        op.f('ix_company_documents_document_type'),
        table_name='company_documents'
    )
    op.drop_index(
        op.f('ix_company_documents_client_id'),
        table_name='company_documents'
    )
    op.drop_table('company_documents')

    # Drop company_partners table
    op.drop_index(
        op.f('ix_company_partners_tenant_id'),
        table_name='company_partners'
    )
    op.drop_index(
        op.f('ix_company_partners_status'),
        table_name='company_partners'
    )
    op.drop_index(
        op.f('ix_company_partners_cpf'),
        table_name='company_partners'
    )
    op.drop_index(
        op.f('ix_company_partners_client_id'),
        table_name='company_partners'
    )
    op.drop_table('company_partners')

    # Drop enum
    op.execute('DROP TYPE IF EXISTS company_document_type_enum')

    # Remove columns from accounting_clients table
    op.drop_index(
        op.f('ix_accounting_clients_responsible_cpf'),
        table_name='accounting_clients'
    )
    op.drop_column('accounting_clients', 'responsible_email')
    op.drop_column('accounting_clients', 'responsible_phone')
    op.drop_column('accounting_clients', 'responsible_address')
    op.drop_column('accounting_clients', 'responsible_cpf')
    op.drop_column('accounting_clients', 'responsible_name')
