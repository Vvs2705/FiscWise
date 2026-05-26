import uuid
from datetime import date, datetime
from typing import Optional, Any, List, Dict

import sqlalchemy as sa
from sqlalchemy import Date, DateTime, ForeignKey, String, Text, UUID as SQLUUID
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase

class EcacProxy(Base, TenantBase):
    """e-CAC Proxy records."""
    __tablename__ = "ecac_proxies"

    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=True,
    )
    outorgante_cpf_cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    outorgante_nome: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    procurador_cpf: Mapped[str] = mapped_column(String(11), nullable=False)
    tipo: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)  # 'e-CAC', 'NFS-e', etc.
    servicos_autorizados: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True, default=[])
    data_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    data_validade: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    status: Mapped[Optional[str]] = mapped_column(String(20), default="ativa", server_default="ativa")
    ultima_verificacao: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Relationships
    client = relationship("AccountingClient", lazy="joined")


class EcacFiscalSituation(Base, TenantBase):
    """e-CAC Fiscal Situation records."""
    __tablename__ = "ecac_fiscal_situations"

    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="CASCADE"),
        nullable=True,
    )
    cpf_cnpj: Mapped[str] = mapped_column(String(14), nullable=False)
    status_geral: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    pendencias: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True, default=[])
    debitos: Mapped[Optional[List[Any]]] = mapped_column(JSONB, nullable=True, default=[])
    certidao_status: Mapped[Optional[str]] = mapped_column(String(30), nullable=True)
    certidao_validade: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    raw_response: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True)
    consultado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), server_default=sa.func.now(), nullable=True)

    # Relationships
    client = relationship("AccountingClient", lazy="joined")
