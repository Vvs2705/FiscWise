"""Operational accounting models for the FiscWise MVP."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional
import enum

from sqlalchemy import Date, DateTime, ForeignKey, Index, JSON, Numeric, String, Text, UUID as SQLUUID, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class InviteStatus(str, enum.Enum):
    """Status of a client portal invite."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    EXPIRED = "expired"


class CompanyDocumentType(str, enum.Enum):
    """Types of company documents."""
    CNPJ = "cnpj"
    CONTRATO_SOCIAL = "contrato_social"
    INSCRICAO_MUNICIPAL = "inscricao_municipal"
    INSCRICAO_ESTADUAL = "inscricao_estadual"
    ALVARA_FUNCIONAMENTO = "alvara_funcionamento"
    LICENCA_SANITARIA = "licenca_sanitaria"
    CNES = "cnes"
    ALVARA_BOMBEIROS = "alvara_bombeiros"
    CRO_JURIDICO = "cro_juridico"


class AccountingClient(Base, TenantBase):
    """Client or taxpayer managed by an accounting office tenant."""

    __tablename__ = "accounting_clients"

    __table_args__ = (
        Index("idx_clients_tenant_status", "tenant_id", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False, default="pj", index=True)
    tax_regime: Mapped[Optional[str]] = mapped_column(String(80), nullable=True, index=True)
    cnae_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    municipal_registration: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    state_registration: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    client_code: Mapped[str] = mapped_column(String(4), nullable=False, default="", index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    monthly_fee: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 2), nullable=True)
    billing_day: Mapped[int] = mapped_column(default=1)
    annual_adjustment_percent: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2), nullable=True,
        comment="Annual fee reajuste % (e.g. 5.00 = 5% IPCA)",
    )
    portal_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    # Responsible person fields
    responsible_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    responsible_cpf: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    responsible_address: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    responsible_phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    responsible_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)


class DeadlineItem(Base, TenantBase):
    """Fiscal, operational, or financial deadline tied to a client."""

    __tablename__ = "deadline_items"

    __table_args__ = (
        Index("idx_deadlines_tenant_due_status", "tenant_id", "due_date", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(80), nullable=False, default="fiscal")
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    priority: Mapped[str] = mapped_column(String(16), nullable=False, default="medium")
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class ClientDocument(Base, TenantBase):
    """Document metadata for client dossiers."""

    __tablename__ = "client_documents"

    __table_args__ = (
        Index("idx_documents_tenant_client_created", "tenant_id", "client_id", "created_at"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document_type: Mapped[str] = mapped_column(String(80), nullable=False, default="other")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="available", index=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    issued_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    expires_at: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parse_status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    parsed_data: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    parse_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DigitalCertificate(Base, TenantBase):
    """Digital certificate metadata for renewal tracking."""

    __tablename__ = "digital_certificates"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    certificate_type: Mapped[str] = mapped_column(String(16), nullable=False, default="a1")
    valid_from: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    valid_until: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="valid", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class AccountReceivable(Base, TenantBase):
    """Receivable billing item for accounting office honorarios."""

    __tablename__ = "account_receivables"

    __table_args__ = (
        Index("idx_receivables_tenant_due_status", "tenant_id", "due_date", "status"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class ClientPortalInvite(Base, TenantBase):
    """Portal access invitation for accounting clients."""

    __tablename__ = "client_portal_invites"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    status: Mapped[InviteStatus] = mapped_column(
        SQLEnum(InviteStatus, name="invite_status_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        default=InviteStatus.PENDING,
        index=True,
    )
    invited_by: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who sent the invite",
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    accepted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class CompanyPartner(Base, TenantBase):
    """Company partner or shareholder information."""

    __tablename__ = "company_partners"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    cpf: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    participation_percentage: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    entry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class CompanyDocument(Base, TenantBase):
    """Company official documents (CNPJ, contracts, licenses, etc.)."""

    __tablename__ = "company_documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_type: Mapped[CompanyDocumentType] = mapped_column(
        SQLEnum(CompanyDocumentType, name="company_document_type_enum", create_type=False, values_callable=lambda x: [e.value for e in x]),
        nullable=False,
        index=True,
    )
    file_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    upload_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=func.now())
    expiration_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="valid", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DasPayment(Base, TenantBase):
    """Monthly Simples Nacional DAS tax payment record for a client."""

    __tablename__ = "das_payments"

    __table_args__ = (
        Index("idx_das_tenant_client_period", "tenant_id", "client_id", "period"),
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # Format: YYYY-MM
    revenue: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", index=True)  # pending, paid, overdue
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    file_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

