"""Operational accounting models for the FiscWise MVP."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class AccountingClient(Base, TenantBase):
    """Client or taxpayer managed by an accounting office tenant."""

    __tablename__ = "accounting_clients"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    document: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    entity_type: Mapped[str] = mapped_column(String(16), nullable=False, default="pj")
    tax_regime: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    phone: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)
    municipal_registration: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    state_registration: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active", index=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class DeadlineItem(Base, TenantBase):
    """Fiscal, operational, or financial deadline tied to a client."""

    __tablename__ = "deadline_items"

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

