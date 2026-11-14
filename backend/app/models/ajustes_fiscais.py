"""Solicitações de ajuste fiscal e ajustes do calendário fiscal.

- FiscalAdjustmentRequest: o escritório pede um ajuste (feriado que falta, prazo
  diferente no estado/município, nova obrigação, outro). Feriado e prazo valem na
  hora só para o escritório; tudo vai para a fila da equipe FiscWise.
- FiscalCalendarAdjustment: o ajuste que o motor de prazos aplica. tenant_id
  NULL = regra geral, sempre limitada à UF/município da regra.
"""

import uuid
from datetime import date, datetime
from typing import Optional

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base

TIPOS_SOLICITACAO = ("feriado", "prazo", "nova_obrigacao", "outro")
TIPOS_APLICAVEIS = ("feriado", "prazo")
STATUS_SOLICITACAO = ("aplicada_no_escritorio", "em_analise", "regra_geral", "recusada")


class FiscalAdjustmentRequest(Base):
    __tablename__ = "fiscal_adjustment_requests"

    id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    municipio_ibge: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    municipio_nome: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    data: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    recorrente_anual: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    obrigacao_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    due_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    descricao: Mapped[str] = mapped_column(Text, nullable=False)
    fonte: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    knowledge_doc_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("rag_documents.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    resposta_equipe: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    reviewed_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class FiscalCalendarAdjustment(Base):
    __tablename__ = "fiscal_calendar_adjustments"

    id: Mapped[uuid.UUID] = mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # NULL = regra geral (vale para todos os escritórios, só na UF/município da regra).
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=True, index=True
    )
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    uf: Mapped[str] = mapped_column(String(2), nullable=False, index=True)
    # NULL = vale para a UF inteira.
    municipio_ibge: Mapped[Optional[str]] = mapped_column(String(7), nullable=True)
    mes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    dia: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    # NULL = todo ano (feriado fixo).
    ano: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    nome: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    obrigacao_code: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    due_day: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")
    origem_request_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True), ForeignKey("fiscal_adjustment_requests.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
