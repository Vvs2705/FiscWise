"""Add obligation engine tables: rules, profiles, instances, checklists

Revision ID: 20260525
Revises: 20260524c
Create Date: 2026-05-25 08:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '20260525'
down_revision = '20260524c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # obligation_rules — global templates (no tenant_id)
    # ------------------------------------------------------------------
    op.create_table(
        'obligation_rules',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=50), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('jurisdiction', sa.String(length=20), nullable=False),   # federal | estadual | municipal
        sa.Column('state', sa.String(length=2), nullable=True),
        sa.Column('applies_to_regimes', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('applies_to_entity_types', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('applies_to_cnaes', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('recurrence', sa.String(length=20), nullable=False),     # monthly | quarterly | yearly | event
        sa.Column('due_day', sa.Integer(), nullable=True),
        sa.Column('requires_employees', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', name='uq_obligation_rules_code'),
    )
    op.create_index('ix_obligation_rules_code', 'obligation_rules', ['code'], unique=True)
    op.create_index('ix_obligation_rules_jurisdiction', 'obligation_rules', ['jurisdiction'], unique=False)
    op.create_index('ix_obligation_rules_active', 'obligation_rules', ['active'], unique=False)

    # ------------------------------------------------------------------
    # client_obligation_profiles — tax profile per client
    # ------------------------------------------------------------------
    op.create_table(
        'client_obligation_profiles',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tax_regime', sa.String(length=30), nullable=True),      # simples_nacional | lucro_presumido | lucro_real | mei
        sa.Column('cnae_main', sa.String(length=10), nullable=True),
        sa.Column('cnae_secondary', postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=2), nullable=True),
        sa.Column('has_employees', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('has_state_registration', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('has_municipal_registration', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_id', name='uq_client_obligation_profiles_client_id'),
    )
    op.create_index('ix_client_obligation_profiles_tenant_id', 'client_obligation_profiles', ['tenant_id'], unique=False)
    op.create_index('ix_client_obligation_profiles_client_id', 'client_obligation_profiles', ['client_id'], unique=True)

    # ------------------------------------------------------------------
    # obligation_instances — concrete obligation per client per month
    # ------------------------------------------------------------------
    op.create_table(
        'obligation_instances',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('rule_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('competence_month', sa.Date(), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('priority', sa.String(length=10), server_default='medium', nullable=False),
        sa.Column('assigned_to', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('delivery_proof', sa.String(length=1024), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['rule_id'], ['obligation_rules.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['assigned_to'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('client_id', 'rule_id', 'competence_month',
                           name='uq_obligation_instance_client_rule_month'),
    )
    op.create_index('ix_obligation_instances_tenant_id', 'obligation_instances', ['tenant_id'], unique=False)
    op.create_index('ix_obligation_instances_client_id', 'obligation_instances', ['client_id'], unique=False)
    op.create_index('ix_obligation_instances_competence_month', 'obligation_instances', ['competence_month'], unique=False)
    op.create_index('ix_obligation_instances_status', 'obligation_instances', ['status'], unique=False)
    op.create_index('ix_obligation_instances_due_date', 'obligation_instances', ['due_date'], unique=False)
    op.create_index('idx_obligations_tenant_month_status',
                    'obligation_instances', ['tenant_id', 'competence_month', 'status'], unique=False)

    # ------------------------------------------------------------------
    # document_checklist_items — checklist per client per month
    # ------------------------------------------------------------------
    op.create_table(
        'document_checklist_items',
        sa.Column('id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', sa.UUID(as_uuid=True), nullable=False),
        sa.Column('obligation_id', sa.UUID(as_uuid=True), nullable=True),
        sa.Column('competence_month', sa.Date(), nullable=False),
        sa.Column('document_name', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=20), server_default='pending', nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['obligation_id'], ['obligation_instances.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_document_checklist_items_tenant_id', 'document_checklist_items', ['tenant_id'], unique=False)
    op.create_index('ix_document_checklist_items_client_id', 'document_checklist_items', ['client_id'], unique=False)
    op.create_index('ix_document_checklist_items_competence_month', 'document_checklist_items', ['competence_month'], unique=False)
    op.create_index('ix_document_checklist_items_status', 'document_checklist_items', ['status'], unique=False)
    op.create_index('idx_checklist_tenant_client_month',
                    'document_checklist_items', ['tenant_id', 'client_id', 'competence_month'], unique=False)

    # ------------------------------------------------------------------
    # Seed data: core Brazilian obligation rules
    # ------------------------------------------------------------------
    op.execute("""
        INSERT INTO obligation_rules (id, code, name, description, jurisdiction, applies_to_regimes,
            applies_to_entity_types, recurrence, due_day, active)
        VALUES
            (gen_random_uuid(), 'DAS', 'DAS — Documento de Arrecadação do Simples Nacional',
             'Guia unificada mensal do Simples Nacional',
             'federal', ARRAY['simples_nacional', 'mei'], ARRAY['pj', 'mei'], 'monthly', 20, true),

            (gen_random_uuid(), 'DEFIS', 'DEFIS — Declaração de Informações Socioeconômicas e Fiscais',
             'Declaração anual do Simples Nacional',
             'federal', ARRAY['simples_nacional'], ARRAY['pj'], 'yearly', 31, true),

            (gen_random_uuid(), 'DCTFWEB', 'DCTFWeb — Declaração de Débitos e Créditos Tributários Federais Web',
             'Declaração mensal de contribuições previdenciárias e FGTS',
             'federal', ARRAY['lucro_presumido', 'lucro_real'], ARRAY['pj'], 'monthly', 15, true),

            (gen_random_uuid(), 'ISS_MENSAL', 'ISS Mensal — Imposto Sobre Serviços',
             'Apuração mensal do ISS para prestadores de serviços',
             'municipal', ARRAY['simples_nacional', 'lucro_presumido', 'lucro_real'], ARRAY['pj'], 'monthly', 20, true),

            (gen_random_uuid(), 'SPED_CONTABIL', 'SPED Contábil — ECD',
             'Escrituração Contábil Digital anual',
             'federal', ARRAY['lucro_presumido', 'lucro_real'], ARRAY['pj'], 'yearly', 31, true),

            (gen_random_uuid(), 'SPED_FISCAL', 'SPED Fiscal — EFD ICMS/IPI',
             'Escrituração Fiscal Digital mensal para ICMS e IPI',
             'estadual', ARRAY['lucro_presumido', 'lucro_real'], ARRAY['pj'], 'monthly', 25, true),

            (gen_random_uuid(), 'ECAC_PARCELAMENTO', 'e-CAC — Acompanhamento de Parcelamentos',
             'Verificação mensal de parcelamentos ativos no e-CAC',
             'federal', ARRAY['simples_nacional', 'lucro_presumido', 'lucro_real'], ARRAY['pj', 'mei'], 'monthly', 30, true),

            (gen_random_uuid(), 'DASN_SIMEI', 'DASN-SIMEI — Declaração Anual do MEI',
             'Declaração anual de faturamento do MEI',
             'federal', ARRAY['mei'], ARRAY['mei'], 'yearly', 31, true),

            (gen_random_uuid(), 'DIRF', 'DIRF — Declaração do Imposto de Renda Retido na Fonte',
             'Declaração anual de IRRF para empresas com retenção',
             'federal', ARRAY['lucro_presumido', 'lucro_real'], ARRAY['pj'], 'yearly', 28, true),

            (gen_random_uuid(), 'RAIS', 'RAIS — Relação Anual de Informações Sociais',
             'Declaração anual de vínculos empregatícios',
             'federal', ARRAY['simples_nacional', 'lucro_presumido', 'lucro_real'], ARRAY['pj'], 'yearly', 31, true)
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_index('idx_checklist_tenant_client_month', table_name='document_checklist_items')
    op.drop_index('ix_document_checklist_items_status', table_name='document_checklist_items')
    op.drop_index('ix_document_checklist_items_competence_month', table_name='document_checklist_items')
    op.drop_index('ix_document_checklist_items_client_id', table_name='document_checklist_items')
    op.drop_index('ix_document_checklist_items_tenant_id', table_name='document_checklist_items')
    op.drop_table('document_checklist_items')

    op.drop_index('idx_obligations_tenant_month_status', table_name='obligation_instances')
    op.drop_index('ix_obligation_instances_due_date', table_name='obligation_instances')
    op.drop_index('ix_obligation_instances_status', table_name='obligation_instances')
    op.drop_index('ix_obligation_instances_competence_month', table_name='obligation_instances')
    op.drop_index('ix_obligation_instances_client_id', table_name='obligation_instances')
    op.drop_index('ix_obligation_instances_tenant_id', table_name='obligation_instances')
    op.drop_table('obligation_instances')

    op.drop_index('ix_client_obligation_profiles_client_id', table_name='client_obligation_profiles')
    op.drop_index('ix_client_obligation_profiles_tenant_id', table_name='client_obligation_profiles')
    op.drop_table('client_obligation_profiles')

    op.drop_index('ix_obligation_rules_active', table_name='obligation_rules')
    op.drop_index('ix_obligation_rules_jurisdiction', table_name='obligation_rules')
    op.drop_index('ix_obligation_rules_code', table_name='obligation_rules')
    op.drop_table('obligation_rules')
