"""e-CAC domain schemas."""
import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict


class FiscalSubjectCreate(BaseModel):
    client_id: Optional[uuid.UUID] = None
    subject_type: str
    document: str
    legal_name: str
    tax_regime: Optional[str] = None
    city_code: Optional[str] = None
    state: Optional[str] = None


class FiscalSubjectOut(FiscalSubjectCreate):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    active: bool
    created_at: datetime


class EcacRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    subject_id: uuid.UUID
    provider: str
    operation: str
    period: Optional[str]
    status: str
    created_at: datetime


class TaxStatusOut(BaseModel):
    subject_id: uuid.UUID
    regularized: Optional[bool]
    pending_count: int
    fetched_at: datetime
    details: Optional[dict] = None
