"""e-CAC / Integra Contador domain models."""
import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import Boolean, ForeignKey, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class EcacSubjectType(str, Enum):
    ACCOUNTANT = "accountant"
    CLIENT = "client"


class FiscalSubject(Base, TenantBase):
    """Sujeito fiscal — contador ou cliente com CPF/CNPJ para consultas e-CAC."""

    __tablename__ = "fiscal_subjects"

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
    subject_type: Mapped[str] = mapped_column(String(20), nullable=False)
    document: Mapped[str] = mapped_column(String(18), nullable=False, index=True)
    legal_name: Mapped[str] = mapped_column(String(255), nullable=False)
    tax_regime: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    city_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EcacCredential(Base, TenantBase):
    """Credencial de acesso ao e-CAC/Integra Contador por subject."""

    __tablename__ = "ecac_credentials"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("fiscal_subjects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    encrypted_credentials: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    certificate_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class EcacRequest(Base, TenantBase):
    """Log de requisições ao e-CAC com idempotência."""

    __tablename__ = "ecac_requests"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("fiscal_subjects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    operation: Mapped[str] = mapped_column(String(60), nullable=False, index=True)
    period: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    idempotency_key: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    request_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    response_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class TaxStatusSnapshot(Base, TenantBase):
    """Snapshot da situação fiscal de um sujeito em determinado momento."""

    __tablename__ = "tax_status_snapshots"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    subject_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("fiscal_subjects.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    raw_payload: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    regularized: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    pending_count: Mapped[int] = mapped_column(nullable=False, default=0)
    fetched_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
