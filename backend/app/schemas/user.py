"""
User Schemas for FiscWise

Pydantic models for User API request/response validation.
"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


class UserBase(BaseModel):
    """Base User schema with common attributes."""
    email: EmailStr = Field(..., description="User email address")
    full_name: Optional[str] = Field(None, max_length=255, description="User full name")
    role: str = Field(default="member", description="User role (owner/admin/member)")
    is_active: bool = Field(default=True, description="Whether user account is active")


class UserCreate(UserBase):
    """Schema for creating a new user."""
    password: str = Field(..., min_length=8, description="User password (min 8 characters)")
    tenant_id: uuid.UUID = Field(..., description="Tenant ID the user belongs to")


class UserResponse(UserBase):
    """Schema for user response (excludes sensitive data)."""
    id: uuid.UUID = Field(..., description="User unique identifier")
    tenant_id: uuid.UUID = Field(..., description="Tenant ID the user belongs to")
    created_at: datetime = Field(..., description="User creation timestamp")
    updated_at: datetime = Field(..., description="User last update timestamp")
    
    class Config:
        from_attributes = True  # Enable ORM mode for SQLAlchemy models
