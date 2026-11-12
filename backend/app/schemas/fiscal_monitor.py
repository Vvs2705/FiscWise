"""Pydantic schemas for Fiscal Monitor integration.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field, model_validator


class FiscalNFeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    access_key: str = Field(..., min_length=44, max_length=44)
    nfe_number: str
    nfe_type: str
    issuer_name: str
    issuer_document: str
    recipient_name: str
    recipient_document: str
    value: Decimal
    issued_at: datetime
    retrieved_at: datetime
    xml_url: Optional[str] = None
    status: str
    created_at: datetime


class FiscalMonitorSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    last_sync_at: Optional[datetime] = None
    cnpj_status: Optional[str] = "REGULAR"
    situation_details: Optional[Dict[str, Any]] = None
    has_debts: bool = False
    debt_count: int = 0
    total_debt_value: Decimal = Decimal("0.00")
    debts_list: Optional[Dict[str, Any]] = None
    cnd_status: Optional[str] = "REGULAR"
    last_cnd_download_at: Optional[datetime] = None
    last_cnd_document_id: Optional[uuid.UUID] = None

    # Origem dos dados cadastrais: "brasilapi" | "mock" | None (nunca consultado
    # ou dado legado do simulador antigo, que não deve ser exibido como real).
    registry_source: Optional[str] = None
    # Débitos, CND e NF-e não são consultados (exigem SERPRO): sempre nulos,
    # com source="unavailable" e a mensagem do que falta.
    debts: Optional[Dict[str, Any]] = None
    cnd: Optional[Dict[str, Any]] = None
    nfes: List[Dict[str, Any]] = Field(default_factory=list)
    source: str = "unavailable"
    message: str = ""

    @model_validator(mode="after")
    def _honest_view(self) -> "FiscalMonitorSummaryResponse":
        from app.services.fiscal_monitor_service import UNAVAILABLE_MESSAGE

        details = self.situation_details or {}
        src = details.get("source")
        self.registry_source = src if src in ("brasilapi", "mock") else None
        if self.registry_source is None and self.cnpj_status not in ("PENDENTE", "ERRO_CONSULTA"):
            # Resumo gravado pelo simulador antigo: não expor como situação real.
            self.cnpj_status = "PENDENTE"
            self.situation_details = None
        self.has_debts = False
        self.debt_count = 0
        self.total_debt_value = Decimal("0.00")
        self.debts_list = None
        self.debts = None
        self.cnd = None
        self.nfes = []
        self.source = "unavailable"
        self.message = UNAVAILABLE_MESSAGE
        return self


class FiscalMonitorSyncResponse(BaseModel):
    status: str
    message: str
    summary: FiscalMonitorSummaryResponse
    nfes_fetched: int = 0
