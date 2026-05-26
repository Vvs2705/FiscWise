"""Pydantic v2 schemas for the invoices domain."""
import uuid
from decimal import Decimal
from typing import Optional
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InvoiceIssuerCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    client_id: Optional[uuid.UUID] = None
    issuer_type: str
    legal_name: str
    document: str
    municipal_registration: Optional[str] = None
    state_registration: Optional[str] = None
    tax_regime: Optional[str] = None
    city_code: Optional[str] = None
    city_name: Optional[str] = None
    state: Optional[str] = None
    provider: str
    certificate_id: Optional[uuid.UUID] = None


class InvoiceIssuerOut(InvoiceIssuerCreate):
    id: uuid.UUID
    active: bool
    created_at: datetime
    updated_at: datetime


class InvoiceServiceProfileCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issuer_id: uuid.UUID
    description: str
    service_code: str
    cnae_code: Optional[str] = None
    iss_rate: Decimal = Field(ge=0, le=1)


class InvoiceServiceProfileOut(InvoiceServiceProfileCreate):
    id: uuid.UUID
    active: bool
    created_at: datetime


class InvoiceCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    issuer_id: uuid.UUID
    customer_client_id: Optional[uuid.UUID] = None
    receivable_id: Optional[uuid.UUID] = None
    invoice_type: str
    competence: str = Field(pattern=r"^\d{4}-\d{2}$")
    service_profile_id: Optional[uuid.UUID] = None
    service_description: str
    service_code: Optional[str] = None
    amount: Decimal = Field(gt=0)
    deductions: Decimal = Field(ge=0, default=Decimal("0"))
    iss_rate: Optional[Decimal] = Field(default=None, ge=0, le=1)
    retained_taxes: Optional[dict] = None
    provider: str


class InvoicePatch(BaseModel):
    service_description: Optional[str] = None
    amount: Optional[Decimal] = Field(default=None, gt=0)
    deductions: Optional[Decimal] = Field(default=None, ge=0)
    retained_taxes: Optional[dict] = None


class InvoiceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    issuer_id: uuid.UUID
    customer_client_id: Optional[uuid.UUID]
    status: str
    invoice_type: str
    competence: str
    service_description: str
    amount: Decimal
    deductions: Decimal
    iss_rate: Optional[Decimal]
    provider: str
    provider_invoice_id: Optional[str]
    verification_code: Optional[str]
    number: Optional[str]
    rejection_reason: Optional[str]
    issued_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime


class InvoiceCancelRequest(BaseModel):
    reason: str = Field(min_length=5)


class InvoiceEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_id: uuid.UUID
    event_type: str
    actor_user_id: Optional[uuid.UUID]
    payload: Optional[dict]
    occurred_at: datetime
