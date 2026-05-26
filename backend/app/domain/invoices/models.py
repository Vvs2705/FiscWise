import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional, Any, Dict

from sqlalchemy import Date, DateTime, ForeignKey, Numeric, String, Text, UUID as SQLUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase

class InvoiceIssuer(Base, TenantBase):
    """Profile of an invoice issuer (emissor)."""
    __tablename__ = "invoice_issuers"

    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    inscricao_municipal: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    regime_tributario: Mapped[str] = mapped_column(String(20), nullable=False)  # simples | lucro_presumido | lucro_real
    municipio_ibge: Mapped[str] = mapped_column(String(7), nullable=False)
    cod_servico_lc116: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    aliquota_iss: Mapped[Optional[Decimal]] = mapped_column(Numeric(5, 4), nullable=True)
    retencao_iss: Mapped[bool] = mapped_column(default=False, server_default="false")

    # Relationships
    client = relationship("AccountingClient", lazy="joined")


class Invoice(Base, TenantBase):
    """NFS-e Invoice record."""
    __tablename__ = "invoices"

    issuer_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("invoice_issuers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(String(20), default="draft", server_default="draft")
    # Statuses: draft | validating | queued | processing | issued | rejected | cancel_requested | cancelled | replaced | failed
    
    numero: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    serie: Mapped[Optional[str]] = mapped_column(String(5), nullable=True)
    competencia: Mapped[date] = mapped_column(Date, nullable=False)
    valor_servico: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    valor_deducoes: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0.00"), server_default="0.00")
    valor_iss: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)
    descricao_servico: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Tomador details
    tomador_nome: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tomador_cpf_cnpj: Mapped[Optional[str]] = mapped_column(String(14), nullable=True)
    tomador_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tomador_municipio_ibge: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    
    # Integration paths / IDs
    provider_protocol: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    provider_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    xml_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    pdf_storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    xml_storage_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    billing_charge_id: Mapped[Optional[uuid.UUID]] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    
    issued_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    issuer = relationship("InvoiceIssuer", lazy="joined")
    client = relationship("AccountingClient", lazy="joined")


class InvoiceEvent(Base, TenantBase):
    """Event log for an invoice."""
    __tablename__ = "invoice_events"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    event_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)


class InvoiceRejection(Base, TenantBase):
    """NFS-e rejection logs."""
    __tablename__ = "invoice_rejections"

    invoice_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    codigo_rejeicao: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
