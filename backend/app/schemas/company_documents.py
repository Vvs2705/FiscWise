"""Schemas for company documents management."""

from datetime import date
from uuid import UUID
from pydantic import BaseModel, Field


class CompanyDocumentBase(BaseModel):
    """Base company document schema."""
    document_type: str = Field(..., description="Type of document (cnpj, contrato_social, etc.)")
    expiration_date: date | None = None
    status: str = Field(default="valid", max_length=32)
    notes: str | None = Field(default=None, max_length=500)


class CompanyDocumentCreate(CompanyDocumentBase):
    """Schema for creating a company document."""
    file_url: str = Field(..., min_length=1, max_length=1024)


class CompanyDocumentUpdate(BaseModel):
    """Schema for updating a company document."""
    document_type: str | None = Field(default=None, description="Type of document")
    expiration_date: date | None = None
    status: str | None = Field(default=None, max_length=32)
    notes: str | None = Field(default=None, max_length=500)


class CompanyDocumentResponse(CompanyDocumentBase):
    """Schema for company document response."""
    id: UUID
    client_id: UUID
    tenant_id: UUID
    file_url: str
    upload_date: str
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True


class CompanyDocumentListResponse(BaseModel):
    """Schema for listing company documents."""
    id: UUID
    document_type: str
    status: str
    upload_date: str
    expiration_date: date | None
    file_url: str

    class Config:
        from_attributes = True
