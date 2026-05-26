"""Fiscal guides (DAS, DARF, DAE, GPS, DCTFWeb) domain models."""
import uuid
from typing import Optional
from enum import Enum

from sqlalchemy import ForeignKey, Numeric, String, Text, Date, DateTime
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from decimal import Decimal

from app.models.base import Base, TenantBase


class GuideType(str, Enum):
    DAS = "DAS"
    DARF = "DARF"
    DAE = "DAE"
    GPS = "GPS"
    DCTFWEB = "DCTFWEB"


class GuideStatus(str, Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    SENT_TO_CUSTOMER = "sent_to_customer"
    AWAITING_PAYMENT = "awaiting_payment"
    PAID = "paid"
    OVERDUE = "overdue"
    CANCELLED = "cancelled"
    DIVERGENT = "divergent"


class FiscalGuide(Base, TenantBase):
    """Guia fiscal (DAS, DARF, etc.) com controle de pagamento."""

    __tablename__ = "fiscal_guides"

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
    subject_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    guide_type: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    competence: Mapped[str] = mapped_column(String(7), nullable=False, index=True)
    due_date: Mapped[object] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    status: Mapped[str] = mapped_column(
        String(25), nullable=False, default=GuideStatus.DRAFT.value, index=True
    )
    barcode: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pix_code: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    provider: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    provider_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    pdf_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    payment_proof_storage_key: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    paid_at: Mapped[Optional[object]] = mapped_column(DateTime(timezone=True), nullable=True)


class FiscalGuideEvent(Base, TenantBase):
    """Eventos de lifecycle de uma guia fiscal."""

    __tablename__ = "fiscal_guide_events"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
    )
    guide_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("fiscal_guides.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    actor_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    occurred_at: Mapped[object] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
