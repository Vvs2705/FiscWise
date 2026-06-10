import uuid
from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, ConfigDict, Field


class ChecklistItemUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    status: str = Field(..., pattern="^(pending|done|blocked|na)$")
    notes: Optional[str] = Field(None, max_length=1000)


class MonthlyClosingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    client_name: Optional[str] = None
    client_cnpj: Optional[str] = None
    competence: str
    status: str
    score: int
    blockers: Optional[List[Any]]
    checklist: Optional[List[Any]]
    invoices_count: int
    invoices_pending: int
    guides_count: int
    guides_paid: int
    obligations_total: int
    obligations_done: int
    ecac_pendencies: int
    documents_total: int
    documents_received: int
    dossier_generated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class GenerateClosingsResult(BaseModel):
    competence: str
    created: int
    skipped: int


class DossierResult(BaseModel):
    url: Optional[str] = None
    generated_at: datetime
