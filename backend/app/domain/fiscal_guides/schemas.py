"""Fiscal guides schemas."""
import uuid
from decimal import Decimal
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict, Field


class FiscalGuideCreate(BaseModel):
    client_id: uuid.UUID
    subject_id: Optional[uuid.UUID] = None
    guide_type: str
    competence: str = Field(pattern=r"^\d{4}-\d{2}$")
    due_date: date
    amount: Decimal = Field(gt=0)
    provider: Optional[str] = None


class FiscalGuideOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    guide_type: str
    competence: str
    due_date: date
    amount: Decimal
    status: str
    barcode: Optional[str]
    paid_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime
