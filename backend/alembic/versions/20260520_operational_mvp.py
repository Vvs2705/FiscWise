"""operational mvp tables

Revision ID: 20260520_operational_mvp
Revises: 20260520_user_foundation
Create Date: 2026-05-20 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260520_operational_mvp"
down_revision: Union[str, None] = "20260520_user_foundation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "accounting_clients",
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("document", sa.String(length=32), nullable=True),
        sa.Column("entity_type", sa.String(length=16), nullable=False),
        sa.Column("tax_regime", sa.String(length=80), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=40), nullable=True),
        sa.Column("municipal_registration", sa.String(length=80), nullable=True),
        sa.Column("state_registration", sa.String(length=80), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False, comment="Primary key UUID"),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Tenant identifier for data isolation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record creation timestamp"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record last update timestamp"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_accounting_clients_document"), "accounting_clients", ["document"], unique=False)
    op.create_index(op.f("ix_accounting_clients_id"), "accounting_clients", ["id"], unique=False)
    op.create_index(op.f("ix_accounting_clients_name"), "accounting_clients", ["name"], unique=False)
    op.create_index(op.f("ix_accounting_clients_status"), "accounting_clients", ["status"], unique=False)
    op.create_index(op.f("ix_accounting_clients_tenant_id"), "accounting_clients", ["tenant_id"], unique=False)

    op.create_table(
        "deadline_items",
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("category", sa.String(length=80), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("priority", sa.String(length=16), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False, comment="Primary key UUID"),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Tenant identifier for data isolation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record creation timestamp"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record last update timestamp"),
        sa.ForeignKeyConstraint(["client_id"], ["accounting_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deadline_items_client_id"), "deadline_items", ["client_id"], unique=False)
    op.create_index(op.f("ix_deadline_items_due_date"), "deadline_items", ["due_date"], unique=False)
    op.create_index(op.f("ix_deadline_items_id"), "deadline_items", ["id"], unique=False)
    op.create_index(op.f("ix_deadline_items_status"), "deadline_items", ["status"], unique=False)
    op.create_index(op.f("ix_deadline_items_tenant_id"), "deadline_items", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_deadline_items_title"), "deadline_items", ["title"], unique=False)

    op.create_table(
        "client_documents",
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("document_type", sa.String(length=80), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("file_url", sa.String(length=1024), nullable=True),
        sa.Column("issued_at", sa.Date(), nullable=True),
        sa.Column("expires_at", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False, comment="Primary key UUID"),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Tenant identifier for data isolation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record creation timestamp"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record last update timestamp"),
        sa.ForeignKeyConstraint(["client_id"], ["accounting_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_client_documents_client_id"), "client_documents", ["client_id"], unique=False)
    op.create_index(op.f("ix_client_documents_expires_at"), "client_documents", ["expires_at"], unique=False)
    op.create_index(op.f("ix_client_documents_id"), "client_documents", ["id"], unique=False)
    op.create_index(op.f("ix_client_documents_name"), "client_documents", ["name"], unique=False)
    op.create_index(op.f("ix_client_documents_status"), "client_documents", ["status"], unique=False)
    op.create_index(op.f("ix_client_documents_tenant_id"), "client_documents", ["tenant_id"], unique=False)

    op.create_table(
        "digital_certificates",
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("certificate_type", sa.String(length=16), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_until", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False, comment="Primary key UUID"),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Tenant identifier for data isolation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record creation timestamp"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record last update timestamp"),
        sa.ForeignKeyConstraint(["client_id"], ["accounting_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_digital_certificates_client_id"), "digital_certificates", ["client_id"], unique=False)
    op.create_index(op.f("ix_digital_certificates_id"), "digital_certificates", ["id"], unique=False)
    op.create_index(op.f("ix_digital_certificates_status"), "digital_certificates", ["status"], unique=False)
    op.create_index(op.f("ix_digital_certificates_tenant_id"), "digital_certificates", ["tenant_id"], unique=False)
    op.create_index(op.f("ix_digital_certificates_valid_until"), "digital_certificates", ["valid_until"], unique=False)

    op.create_table(
        "account_receivables",
        sa.Column("client_id", sa.UUID(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False, comment="Primary key UUID"),
        sa.Column("tenant_id", sa.UUID(), nullable=False, comment="Tenant identifier for data isolation"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record creation timestamp"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False, comment="Record last update timestamp"),
        sa.ForeignKeyConstraint(["client_id"], ["accounting_clients.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_account_receivables_client_id"), "account_receivables", ["client_id"], unique=False)
    op.create_index(op.f("ix_account_receivables_due_date"), "account_receivables", ["due_date"], unique=False)
    op.create_index(op.f("ix_account_receivables_id"), "account_receivables", ["id"], unique=False)
    op.create_index(op.f("ix_account_receivables_status"), "account_receivables", ["status"], unique=False)
    op.create_index(op.f("ix_account_receivables_tenant_id"), "account_receivables", ["tenant_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_account_receivables_tenant_id"), table_name="account_receivables")
    op.drop_index(op.f("ix_account_receivables_status"), table_name="account_receivables")
    op.drop_index(op.f("ix_account_receivables_id"), table_name="account_receivables")
    op.drop_index(op.f("ix_account_receivables_due_date"), table_name="account_receivables")
    op.drop_index(op.f("ix_account_receivables_client_id"), table_name="account_receivables")
    op.drop_table("account_receivables")
    op.drop_index(op.f("ix_digital_certificates_valid_until"), table_name="digital_certificates")
    op.drop_index(op.f("ix_digital_certificates_tenant_id"), table_name="digital_certificates")
    op.drop_index(op.f("ix_digital_certificates_status"), table_name="digital_certificates")
    op.drop_index(op.f("ix_digital_certificates_id"), table_name="digital_certificates")
    op.drop_index(op.f("ix_digital_certificates_client_id"), table_name="digital_certificates")
    op.drop_table("digital_certificates")
    op.drop_index(op.f("ix_client_documents_tenant_id"), table_name="client_documents")
    op.drop_index(op.f("ix_client_documents_status"), table_name="client_documents")
    op.drop_index(op.f("ix_client_documents_name"), table_name="client_documents")
    op.drop_index(op.f("ix_client_documents_id"), table_name="client_documents")
    op.drop_index(op.f("ix_client_documents_expires_at"), table_name="client_documents")
    op.drop_index(op.f("ix_client_documents_client_id"), table_name="client_documents")
    op.drop_table("client_documents")
    op.drop_index(op.f("ix_deadline_items_title"), table_name="deadline_items")
    op.drop_index(op.f("ix_deadline_items_tenant_id"), table_name="deadline_items")
    op.drop_index(op.f("ix_deadline_items_status"), table_name="deadline_items")
    op.drop_index(op.f("ix_deadline_items_id"), table_name="deadline_items")
    op.drop_index(op.f("ix_deadline_items_due_date"), table_name="deadline_items")
    op.drop_index(op.f("ix_deadline_items_client_id"), table_name="deadline_items")
    op.drop_table("deadline_items")
    op.drop_index(op.f("ix_accounting_clients_tenant_id"), table_name="accounting_clients")
    op.drop_index(op.f("ix_accounting_clients_status"), table_name="accounting_clients")
    op.drop_index(op.f("ix_accounting_clients_name"), table_name="accounting_clients")
    op.drop_index(op.f("ix_accounting_clients_id"), table_name="accounting_clients")
    op.drop_index(op.f("ix_accounting_clients_document"), table_name="accounting_clients")
    op.drop_table("accounting_clients")
