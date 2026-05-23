from datetime import date, datetime
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


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
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    client_id: UUID
    tenant_id: UUID
    file_url: str
    upload_date: datetime
    created_at: datetime
    updated_at: datetime


class CompanyDocumentListResponse(BaseModel):
    """Schema for listing company documents."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_type: str
    status: str
    upload_date: datetime
    expiration_date: date | None
    file_url: str
