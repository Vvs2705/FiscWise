from datetime import date, datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class DasPaymentCreate(BaseModel):
    """Schema for registering a monthly DAS payment."""

    model_config = ConfigDict(str_strip_whitespace=True)

    client_id: UUID = Field(..., description="ID of the client")
    period: str = Field(..., min_length=7, max_length=7, description="Reference period formatted as YYYY-MM", examples=["2026-01"])
    revenue: Decimal = Field(default=Decimal("0.00"), ge=0, description="Declared gross revenue for the month")
    tax_amount: Decimal = Field(..., ge=0, description="DAS tax amount due")
    due_date: date = Field(..., description="DAS due date")
    status: str = Field(default="pending", description="Payment status: pending or paid")
    notes: Optional[str] = Field(default=None, max_length=1000)

    @field_validator("period")
    @classmethod
    def validate_period_format(cls, v: str) -> str:
        parts = v.split("-")
        if len(parts) != 2 or len(parts[0]) != 4 or len(parts[1]) != 2:
            raise ValueError("Period must be formatted as YYYY-MM")
        try:
            year, month = int(parts[0]), int(parts[1])
            if month < 1 or month > 12:
                raise ValueError("Month must be between 01 and 12")
        except ValueError:
            raise ValueError("Period must contain valid integer numbers")
        return v


class DasPaymentUpdate(BaseModel):
    """Schema for updating a DAS payment entry."""

    model_config = ConfigDict(str_strip_whitespace=True)

    revenue: Optional[Decimal] = Field(default=None, ge=0)
    tax_amount: Optional[Decimal] = Field(default=None, ge=0)
    due_date: Optional[date] = None
    status: Optional[str] = Field(default=None, description="pending, paid")
    file_url: Optional[str] = Field(default=None, max_length=1024)
    notes: Optional[str] = Field(default=None, max_length=1000)


class DasPaymentResponse(BaseModel):
    """Schema representing a DAS payment entry in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    client_name: Optional[str] = None
    period: str
    revenue: Decimal
    tax_amount: Decimal
    due_date: date
    status: str
    paid_at: Optional[datetime] = None
    file_url: Optional[str] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
