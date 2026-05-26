"""Invoice / NFS-e domain models."""
import uuid
from decimal import Decimal
from typing import Optional
from enum import Enum

from sqlalchemy import (
    Boolean, ForeignKey, Numeric, String, Text, UniqueConstraint,
    DateTime, Date,
)
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class InvoiceStatus(str, Enum):
    DRAFT = "draft"
    VALIDATING = "validating"
    READY_TO_ISSUE = "ready_to_issue"
    ISSUING = "issuing"
    PROCESSING = "processing"
    ISSUED = "issued"
    REJECTED = "rejected"
    CANCEL_REQUESTED = "cancel_requested"
    CANCELLED = "cancelled"
    FAILED = "failed"


class InvoiceType(str, Enum):
    HONORARIOS = "honorarios"
    SERVICO_AVULSO = "servico_avulso"
    CLIENTE_PRESTADOR = "cliente_prestador"


class IssuerType(str, Enum):
    ACCOUNTANT = "accountant"
    CLIENT = "client"


class InvoiceIssuer(Base, TenantBase):
    """Cadastro de emissores de NFS-e (contador ou cliente autorizado)."""

    __tablename__ = "invoice_issuers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    issuer_type: Mapped[str] = mapped_column(String(20), nullable=False)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    document: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    municipal_registration: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    state_registration: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    tax_regime: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    city_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    city_name: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    certificate_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class InvoiceServiceProfile(Base, TenantBase):
    """Perfil de serviço para NFS-e (CNAE + código de serviço + alíquota)."""

    __tablename__ = "invoice_service_profiles"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    issuer_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("invoice_issuers.id", ondelete="CASCADE"),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    service_code: Mapped[str] = mapped_column(String(20), nullable=False)
    cnae_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    iss_rate: Mapped[Decimal] = mapped_column(Numeric(5, 4), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class Invoice(Base, TenantBase):
    """Nota fiscal de serviço (NFS-e)."""

    __tablename__ = "invoices"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    issuer_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("invoice_issuers.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    customer_client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True, index=True,
    )
    receivable_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(30), nullable=False, default=InvoiceStatus.DRAFT.value, index=True
    )
    invoice_type: Mapped[str] = mapped_column(String(30), nullable=False)
    competence: Mapped[str] = mapped_column(String(7), nullable=False, index=True)  # YYYY-MM
    service_profile_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    service_description: Mapped[str] = mapped_column(Text, nullable=False)
    service_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    deductions: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0"))
    iss_rate: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    retained_taxes: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    # Provider fields
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_invoice_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    provider_protocol: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    verification_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    number: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    series: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    # Storage
    xml_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    pdf_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    danfse_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    # Status fields
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    issued_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)


class InvoiceEvent(Base, TenantBase):
    """Log de eventos de ciclo de vida de uma nota fiscal."""

    __tablename__ = "invoice_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    occurred_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
