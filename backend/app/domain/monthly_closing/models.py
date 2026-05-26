"""Monthly Closing domain models — fechamento mensal contábil-fiscal."""
import uuid
from typing import Optional
from enum import Enum
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String, Text, Date, DateTime, Boolean
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class ClosingStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    PENDING_REVIEW = "pending_review"
    CLOSED = "closed"
    REOPENED = "reopened"


class ClosingItemType(str, Enum):
    INVOICE = "invoice"
    GUIDE = "guide"            # Guia fiscal (DAS/DARF/etc.)
    OBLIGATION = "obligation"  # Obrigação acessória
    CERTIFICATE = "certificate"
    DOCUMENT = "document"
    OTHER = "other"


class ClosingItemStatus(str, Enum):
    PENDING = "pending"
    OK = "ok"
    DIVERGENT = "divergent"
    WAIVED = "waived"


class MonthlyClosing(Base, TenantBase):
    """Fechamento mensal de um cliente para uma competência."""

    __tablename__ = "monthly_closings"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    competence: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(25), nullable=False, default=ClosingStatus.OPEN.value, index=True
    )
    responsible_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_revenue: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    total_tax: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    closed_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
    dossier_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    summary_json: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)


class MonthlyClosingItem(Base, TenantBase):
    """Item individual dentro de um fechamento mensal (NF, guia, obrigação...)."""

    __tablename__ = "monthly_closing_items"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    closing_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("monthly_closings.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    item_type: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    item_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=ClosingItemStatus.PENDING.value
    )
    reference_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), nullable=True
    )
    description: Mapped[str] = mapped_column(String(500), nullable=False)
    amount: Mapped[Optional[Decimal]] = mapped_column(Numeric(14, 2), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    is_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class FiscalDossier(Base, TenantBase):
    """Dossiê fiscal mensal gerado ao fechar competência."""

    __tablename__ = "fiscal_dossiers"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    closing_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("monthly_closings.id", ondelete="CASCADE"),
        nullable=False, unique=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )
    competence: Mapped[str] = mapped_column(String(7), nullable=False)
    storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sent_to_client: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sent_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)
    pages: Mapped[Optional[int]] = mapped_column(nullable=True)
