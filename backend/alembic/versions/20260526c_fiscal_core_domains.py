"""Fiscal Core Domains — invoices, ecac, certificates, powers_of_attorney,
fiscal_guides, fiscal_mailbox, monthly_closing, fiscal_dossiers

Revision ID: 20260526c
Revises: 20260526b
Create Date: 2026-05-26 14:00:00.000000
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260526c'
down_revision = '20260526b'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── Invoice Issuers ──────────────────────────────────────────────────────
    op.create_table(
        'invoice_issuers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('issuer_type', sa.String(20), nullable=False),
        sa.Column('document', sa.String(18), nullable=False),
        sa.Column('legal_name', sa.String(200), nullable=False),
        sa.Column('trade_name', sa.String(200), nullable=True),
        sa.Column('municipality_code', sa.String(10), nullable=True),
        sa.Column('tax_regime', sa.String(30), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_invoice_issuers_tenant_id', 'invoice_issuers', ['tenant_id'])
    op.create_index('ix_invoice_issuers_client_id', 'invoice_issuers', ['client_id'])
    op.create_index('ix_invoice_issuers_document', 'invoice_issuers', ['document'])

    # ── Invoice Service Profiles ─────────────────────────────────────────────
    op.create_table(
        'invoice_service_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('issuer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('cnae_code', sa.String(10), nullable=True),
        sa.Column('service_code', sa.String(20), nullable=True),
        sa.Column('iss_rate', sa.Numeric(5, 4), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['issuer_id'], ['invoice_issuers.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_invoice_service_profiles_tenant_id', 'invoice_service_profiles', ['tenant_id'])
    op.create_index('ix_invoice_service_profiles_issuer_id', 'invoice_service_profiles', ['issuer_id'])

    # ── Invoices ─────────────────────────────────────────────────────────────
    op.create_table(
        'invoices',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('issuer_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('service_profile_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('invoice_type', sa.String(20), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='draft'),
        sa.Column('competence', sa.String(7), nullable=False),
        sa.Column('issue_date', sa.Date(), nullable=True),
        sa.Column('service_description', sa.Text(), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=False),
        sa.Column('iss_amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('provider_id', sa.String(200), nullable=True),
        sa.Column('provider_number', sa.String(50), nullable=True),
        sa.Column('xml_storage_key', sa.String(500), nullable=True),
        sa.Column('pdf_storage_key', sa.String(500), nullable=True),
        sa.Column('taker_document', sa.String(18), nullable=True),
        sa.Column('taker_name', sa.String(200), nullable=True),
        sa.Column('cancellation_reason', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.ForeignKeyConstraint(['issuer_id'], ['invoice_issuers.id'], ondelete='RESTRICT'),
        sa.ForeignKeyConstraint(['service_profile_id'], ['invoice_service_profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_invoices_tenant_id', 'invoices', ['tenant_id'])
    op.create_index('ix_invoices_client_id', 'invoices', ['client_id'])
    op.create_index('ix_invoices_issuer_id', 'invoices', ['issuer_id'])
    op.create_index('ix_invoices_status', 'invoices', ['status'])
    op.create_index('ix_invoices_competence', 'invoices', ['competence'])

    # ── Invoice Events ────────────────────────────────────────────────────────
    op.create_table(
        'invoice_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('invoice_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(60), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payload', postgresql.JSONB(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['invoice_id'], ['invoices.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_invoice_events_invoice_id', 'invoice_events', ['invoice_id'])

    # ── Fiscal Subjects (e-CAC) ──────────────────────────────────────────────
    op.create_table(
        'fiscal_subjects',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('document', sa.String(18), nullable=False),
        sa.Column('name', sa.String(200), nullable=True),
        sa.Column('subject_type', sa.String(20), nullable=False),
        sa.Column('tax_regime', sa.String(30), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fiscal_subjects_tenant_id', 'fiscal_subjects', ['tenant_id'])
    op.create_index('ix_fiscal_subjects_document', 'fiscal_subjects', ['document'])

    # ── e-CAC Credentials ─────────────────────────────────────────────────────
    op.create_table(
        'ecac_credentials',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('credential_type', sa.String(30), nullable=False),
        sa.Column('certificate_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['fiscal_subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_ecac_credentials_tenant_id', 'ecac_credentials', ['tenant_id'])
    op.create_index('ix_ecac_credentials_subject_id', 'ecac_credentials', ['subject_id'])

    # ── e-CAC Requests (idempotent) ───────────────────────────────────────────
    op.create_table(
        'ecac_requests',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('idempotency_key', sa.String(100), nullable=False),
        sa.Column('request_type', sa.String(60), nullable=False),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('request_payload', postgresql.JSONB(), nullable=True),
        sa.Column('response_payload', postgresql.JSONB(), nullable=True),
        sa.Column('error_detail', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['fiscal_subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('idempotency_key', name='uq_ecac_requests_idempotency_key'),
    )
    op.create_index('ix_ecac_requests_tenant_id', 'ecac_requests', ['tenant_id'])
    op.create_index('ix_ecac_requests_subject_id', 'ecac_requests', ['subject_id'])

    # ── Tax Status Snapshots ─────────────────────────────────────────────────
    op.create_table(
        'tax_status_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('snapshot_date', sa.Date(), nullable=False),
        sa.Column('status_code', sa.String(20), nullable=False),
        sa.Column('regularities', postgresql.JSONB(), nullable=True),
        sa.Column('debts', postgresql.JSONB(), nullable=True),
        sa.Column('raw_response', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['subject_id'], ['fiscal_subjects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_tax_status_snapshots_tenant_id', 'tax_status_snapshots', ['tenant_id'])
    op.create_index('ix_tax_status_snapshots_subject_id', 'tax_status_snapshots', ['subject_id'])

    # NOTE: digital_certificates table already created in 20260520_operational_mvp.py
    # ── Certificate Usage Events (new — audit trail for cert accesses) ───────
    op.create_table(
        'certificate_usage_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('certificate_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('operation', sa.String(60), nullable=False),
        sa.Column('metadata', postgresql.JSONB(), nullable=True),
        sa.Column('used_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['certificate_id'], ['digital_certificates.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_certificate_usage_events_tenant_id', 'certificate_usage_events', ['tenant_id'])
    op.create_index('ix_certificate_usage_events_certificate_id', 'certificate_usage_events', ['certificate_id'])

    # ── Powers of Attorney ────────────────────────────────────────────────────
    op.create_table(
        'powers_of_attorney',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('grantor_document', sa.String(18), nullable=False),
        sa.Column('attorney_document', sa.String(18), nullable=False),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('services', postgresql.JSONB(), nullable=True),
        sa.Column('valid_from', sa.Date(), nullable=True),
        sa.Column('valid_until', sa.Date(), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('last_checked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_powers_of_attorney_tenant_id', 'powers_of_attorney', ['tenant_id'])
    op.create_index('ix_powers_of_attorney_client_id', 'powers_of_attorney', ['client_id'])
    op.create_index('ix_powers_of_attorney_grantor_document', 'powers_of_attorney', ['grantor_document'])
    op.create_index('ix_powers_of_attorney_attorney_document', 'powers_of_attorney', ['attorney_document'])
    op.create_index('ix_powers_of_attorney_valid_until', 'powers_of_attorney', ['valid_until'])
    op.create_index('ix_powers_of_attorney_status', 'powers_of_attorney', ['status'])

    # ── Fiscal Guides ─────────────────────────────────────────────────────────
    op.create_table(
        'fiscal_guides',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('guide_type', sa.String(10), nullable=False),
        sa.Column('competence', sa.String(7), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('status', sa.String(25), nullable=False, server_default='draft'),
        sa.Column('barcode', sa.String(100), nullable=True),
        sa.Column('pix_code', sa.Text(), nullable=True),
        sa.Column('provider', sa.String(50), nullable=True),
        sa.Column('provider_id', sa.String(100), nullable=True),
        sa.Column('pdf_storage_key', sa.String(500), nullable=True),
        sa.Column('payment_proof_storage_key', sa.String(500), nullable=True),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fiscal_guides_tenant_id', 'fiscal_guides', ['tenant_id'])
    op.create_index('ix_fiscal_guides_client_id', 'fiscal_guides', ['client_id'])
    op.create_index('ix_fiscal_guides_guide_type', 'fiscal_guides', ['guide_type'])
    op.create_index('ix_fiscal_guides_competence', 'fiscal_guides', ['competence'])
    op.create_index('ix_fiscal_guides_due_date', 'fiscal_guides', ['due_date'])
    op.create_index('ix_fiscal_guides_status', 'fiscal_guides', ['status'])

    # ── Fiscal Guide Events ───────────────────────────────────────────────────
    op.create_table(
        'fiscal_guide_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('guide_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('event_type', sa.String(60), nullable=False),
        sa.Column('actor_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['guide_id'], ['fiscal_guides.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fiscal_guide_events_guide_id', 'fiscal_guide_events', ['guide_id'])

    # ── Fiscal Mailbox Messages ───────────────────────────────────────────────
    op.create_table(
        'fiscal_mailbox_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('provider', sa.String(50), nullable=False),
        sa.Column('provider_message_id', sa.String(200), nullable=True),
        sa.Column('message_type', sa.String(30), nullable=False, server_default='other'),
        sa.Column('status', sa.String(20), nullable=False, server_default='unread'),
        sa.Column('sender', sa.String(200), nullable=True),
        sa.Column('subject', sa.String(500), nullable=False),
        sa.Column('body_text', sa.Text(), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('has_attachment', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('attachment_storage_key', sa.String(500), nullable=True),
        sa.Column('metadata_json', postgresql.JSONB(), nullable=True),
        sa.Column('is_urgent', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='SET NULL'),
        sa.UniqueConstraint('provider_message_id', name='uq_fiscal_mailbox_provider_message_id'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fiscal_mailbox_messages_tenant_id', 'fiscal_mailbox_messages', ['tenant_id'])
    op.create_index('ix_fiscal_mailbox_messages_client_id', 'fiscal_mailbox_messages', ['client_id'])
    op.create_index('ix_fiscal_mailbox_messages_provider', 'fiscal_mailbox_messages', ['provider'])
    op.create_index('ix_fiscal_mailbox_messages_status', 'fiscal_mailbox_messages', ['status'])
    op.create_index('ix_fiscal_mailbox_messages_message_type', 'fiscal_mailbox_messages', ['message_type'])
    op.create_index('ix_fiscal_mailbox_messages_received_at', 'fiscal_mailbox_messages', ['received_at'])

    # ── Monthly Closings ──────────────────────────────────────────────────────
    op.create_table(
        'monthly_closings',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competence', sa.String(7), nullable=False),
        sa.Column('status', sa.String(25), nullable=False, server_default='open'),
        sa.Column('responsible_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('total_revenue', sa.Numeric(14, 2), nullable=True),
        sa.Column('total_tax', sa.Numeric(14, 2), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dossier_storage_key', sa.String(500), nullable=True),
        sa.Column('summary_json', postgresql.JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='RESTRICT'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_monthly_closings_tenant_id', 'monthly_closings', ['tenant_id'])
    op.create_index('ix_monthly_closings_client_id', 'monthly_closings', ['client_id'])
    op.create_index('ix_monthly_closings_competence', 'monthly_closings', ['competence'])
    op.create_index('ix_monthly_closings_status', 'monthly_closings', ['status'])

    # ── Monthly Closing Items ─────────────────────────────────────────────────
    op.create_table(
        'monthly_closing_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('closing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_type', sa.String(20), nullable=False),
        sa.Column('item_status', sa.String(20), nullable=False, server_default='pending'),
        sa.Column('reference_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('description', sa.String(500), nullable=False),
        sa.Column('amount', sa.Numeric(14, 2), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('is_required', sa.Boolean(), nullable=False, server_default='true'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['closing_id'], ['monthly_closings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_monthly_closing_items_closing_id', 'monthly_closing_items', ['closing_id'])
    op.create_index('ix_monthly_closing_items_item_type', 'monthly_closing_items', ['item_type'])

    # ── Fiscal Dossiers ───────────────────────────────────────────────────────
    op.create_table(
        'fiscal_dossiers',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('closing_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('competence', sa.String(7), nullable=False),
        sa.Column('storage_key', sa.String(500), nullable=True),
        sa.Column('sent_to_client', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pages', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['closing_id'], ['monthly_closings.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['client_id'], ['accounting_clients.id'], ondelete='RESTRICT'),
        sa.UniqueConstraint('closing_id', name='uq_fiscal_dossiers_closing_id'),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_fiscal_dossiers_tenant_id', 'fiscal_dossiers', ['tenant_id'])
    op.create_index('ix_fiscal_dossiers_client_id', 'fiscal_dossiers', ['client_id'])


def downgrade() -> None:
    op.drop_table('fiscal_dossiers')
    op.drop_table('monthly_closing_items')
    op.drop_table('monthly_closings')
    op.drop_table('fiscal_mailbox_messages')
    op.drop_table('fiscal_guide_events')
    op.drop_table('fiscal_guides')
    op.drop_table('powers_of_attorney')
    op.drop_table('certificate_usage_events')
    # NOTE: digital_certificates is NOT dropped here — it pre-dates this migration
    op.drop_table('tax_status_snapshots')
    op.drop_table('ecac_requests')
    op.drop_table('ecac_credentials')
    op.drop_table('fiscal_subjects')
    op.drop_table('invoice_events')
    op.drop_table('invoices')
    op.drop_table('invoice_service_profiles')
    op.drop_table('invoice_issuers')
