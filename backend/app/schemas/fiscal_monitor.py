"""Pydantic schemas for Fiscal Monitor integration.
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


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


class FiscalMonitorSyncResponse(BaseModel):
    status: str
    message: str
    summary: FiscalMonitorSummaryResponse
    nfes_fetched: int
