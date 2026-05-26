"""Powers of Attorney schemas."""
import uuid
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class PoaCreate(BaseModel):
    client_id: Optional[uuid.UUID] = None
    grantor_document: str
    attorney_document: str
    provider: str
    services: Optional[list[str]] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None


class PoaPatch(BaseModel):
    services: Optional[list[str]] = None
    valid_from: Optional[date] = None
    valid_until: Optional[date] = None
    status: Optional[str] = None


class PoaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: Optional[uuid.UUID]
    grantor_document: str
    attorney_document: str
    provider: str
    services: Optional[list]
    valid_from: Optional[date]
    valid_until: Optional[date]
    status: str
    last_checked_at: Optional[datetime]
    created_at: datetime
