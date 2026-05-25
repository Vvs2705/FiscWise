"""SQLAlchemy models for Fiscal Monitor integration.

Tables:
  fiscal_monitor_summaries  — stores general CNPJ status, debts lists, and CND records
  fiscal_nfes               — tracks invoice details retrieved from Receita Federal
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    DateTime, ForeignKey, Numeric, String, Text, JSON, Boolean,
    UUID as SQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase


class FiscalMonitorSummary(Base, TenantBase):
    """
    Representa a situação fiscal geral de um CNPJ monitorado via parceiro.
    Armazena o status cadastral, CND federal e resumo de débitos.
    """

    __tablename__ = "fiscal_monitor_summaries"

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
        unique=True,
        index=True,
        comment="Cliente contábil monitorado",
    )
    last_sync_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Última sincronização com o parceiro",
    )
    cnpj_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default="REGULAR",
        comment="Status do CNPJ (ex: REGULAR, SUSPENSA, INAPTA)",
    )
    situation_details: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Detalhes cadastrais completos do CNPJ",
    )
    has_debts: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Se há débitos ativos no momento da verificação",
    )
    debt_count: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
        comment="Quantidade de pendências financeiras fiscais encontradas",
    )
    total_debt_value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.00"),
        comment="Valor consolidado dos débitos ativos",
    )
    debts_list: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True,
        comment="Lista descritiva detalhada dos débitos/pendências",
    )
    cnd_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        default="REGULAR",
        comment="Status da CND (ex: REGULAR, COM_PENDENCIAS, EXPIRADA)",
    )
    last_cnd_download_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Data do último download da CND oficial",
    )
    last_cnd_document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("client_documents.id", ondelete="SET NULL"),
        nullable=True,
        comment="Documento correspondente à última CND baixada no dossiê",
    )

    # Relationships
    client = relationship("AccountingClient", foreign_keys=[client_id])
    cnd_document = relationship("ClientDocument", foreign_keys=[last_cnd_document_id])


class FiscalNFe(Base, TenantBase):
    """
    Representa uma Nota Fiscal Eletrônica (NF-e) capturada da Receita Federal.
    """

    __tablename__ = "fiscal_nfes"

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
        comment="Cliente relacionado à NF-e",
    )
    access_key: Mapped[str] = mapped_column(
        String(44),
        nullable=False,
        unique=True,
        index=True,
        comment="Chave de acesso da NF-e com 44 dígitos",
    )
    nfe_number: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Número da nota fiscal",
    )
    nfe_type: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        index=True,
        comment="Tipo da nota: ENTRADA | SAIDA",
    )
    issuer_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Razão Social / Nome do Emitente",
    )
    issuer_document: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="CNPJ ou CPF do Emitente",
    )
    recipient_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Razão Social / Nome do Destinatário",
    )
    recipient_document: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        comment="CNPJ ou CPF do Destinatário",
    )
    value: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Valor total da nota fiscal",
    )
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data de emissão da NF-e",
    )
    retrieved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        comment="Data da consulta/retorno da nota",
    )
    xml_url: Mapped[Optional[str]] = mapped_column(
        String(1024),
        nullable=True,
        comment="URL do XML assinado da NF-e",
    )
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="AUTORIZADA",
        index=True,
        comment="Status da NF-e: AUTORIZADA | CANCELADA",
    )

    # Relationships
    client = relationship("AccountingClient", foreign_keys=[client_id])
