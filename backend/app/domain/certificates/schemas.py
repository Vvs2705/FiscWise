"""Certificate domain schemas — mapped to app.models.operations.DigitalCertificate."""
import uuid
from typing import Optional
from datetime import date, datetime
from pydantic import BaseModel, ConfigDict


class CertificateCreate(BaseModel):
    client_id: uuid.UUID
    label: str
    certificate_type: str = "a1"
    valid_from: Optional[date] = None
    valid_until: date
    status: str = "valid"
    notes: Optional[str] = None


class CertificatePatch(BaseModel):
    label: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


class CertificateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    client_id: uuid.UUID
    label: str
    certificate_type: str
    valid_from: Optional[date]
    valid_until: date
    status: str
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
