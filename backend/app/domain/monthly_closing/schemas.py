"""Monthly Closing schemas."""
import uuid
from typing import Optional
from decimal import Decimal
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class MonthlyClosingCreate(BaseModel):
    client_id: uuid.UUID
    competence: str = Field(pattern=r"^\d{4}-\d{2}$")
    responsible_user_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None


class MonthlyClosingPatch(BaseModel):
    status: Optional[str] = None
    responsible_user_id: Optional[uuid.UUID] = None
    notes: Optional[str] = None
    total_revenue: Optional[Decimal] = None
    total_tax: Optional[Decimal] = None


class MonthlyClosingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    competence: str
    status: str
    responsible_user_id: Optional[uuid.UUID]
    notes: Optional[str]
    total_revenue: Optional[Decimal]
    total_tax: Optional[Decimal]
    closed_at: Optional[datetime]
    dossier_storage_key: Optional[str]
    created_at: datetime
    updated_at: datetime


class ClosingItemCreate(BaseModel):
    item_type: str
    description: str
    reference_id: Optional[uuid.UUID] = None
    amount: Optional[Decimal] = None
    notes: Optional[str] = None
    is_required: bool = True


class ClosingItemPatch(BaseModel):
    item_status: Optional[str] = None
    notes: Optional[str] = None
    amount: Optional[Decimal] = None


class ClosingItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    closing_id: uuid.UUID
    item_type: str
    item_status: str
    reference_id: Optional[uuid.UUID]
    description: str
    amount: Optional[Decimal]
    notes: Optional[str]
    is_required: bool
    created_at: datetime


class FiscalDossierOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    closing_id: uuid.UUID
    client_id: uuid.UUID
    competence: str
    storage_key: Optional[str]
    sent_to_client: bool
    sent_at: Optional[datetime]
    pages: Optional[int]
    created_at: datetime
