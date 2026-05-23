"""Schemas for company partners management."""

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


class PartnerBase(BaseModel):
    """Base partner schema."""
    name: str = Field(..., min_length=1, max_length=255)
    cpf: str = Field(..., min_length=11, max_length=20)
    participation_percentage: Decimal = Field(..., ge=0, le=100, decimal_places=2)
    entry_date: date | None = None
    status: str = Field(default="active", max_length=32)
    notes: str | None = Field(default=None, max_length=500)


class PartnerCreate(PartnerBase):
    """Schema for creating a partner."""
    pass


class PartnerUpdate(BaseModel):
    """Schema for updating a partner."""
    name: str | None = Field(default=None, min_length=1, max_length=255)
    cpf: str | None = Field(default=None, min_length=11, max_length=20)
    participation_percentage: Decimal | None = Field(default=None, ge=0, le=100, decimal_places=2)
    entry_date: date | None = None
    status: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=500)


class PartnerResponse(PartnerBase):
    """Schema for partner response."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    tenant_id: UUID
    created_at: datetime
    updated_at: datetime
