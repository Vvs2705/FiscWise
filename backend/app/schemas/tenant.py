"""
Tenant Schemas for ContaFlow

Pydantic models for Tenant API request/response validation.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class TenantBase(BaseModel):
    """Base Tenant schema with common attributes."""
    name: str = Field(..., min_length=1, max_length=255, description="Organization or company name")
    document: Optional[str] = Field(None, max_length=32, description="CNPJ or CPF (Brazilian tax ID)")


class TenantCreate(TenantBase):
    """Schema for creating a new tenant."""
    pass


class TenantResponse(TenantBase):
    """Schema for tenant response."""
    id: uuid.UUID = Field(..., description="Tenant unique identifier")
    subscription_status: str = Field(..., description="Current subscription status")
    created_at: datetime = Field(..., description="Tenant creation timestamp")
    updated_at: datetime = Field(..., description="Tenant last update timestamp")
    
    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models
