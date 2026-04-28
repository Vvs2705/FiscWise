"""
Knowledge Base Schemas for ContaFlow

Pydantic models for knowledge base API request/response validation.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, HttpUrl
from typing import Optional
from app.models.knowledge import DocumentStatus


class IngestTextRequest(BaseModel):
    """Request schema for ingesting raw text."""
    title: str
    content: str


class IngestURLRequest(BaseModel):
    """Request schema for ingesting content from a URL."""
    url: str
    title: Optional[str] = None


class DocumentResponse(BaseModel):
    """Response schema for document information."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    content_type: str
    status: DocumentStatus
    created_at: datetime
    chunk_count: int = 0

    class Config:
        from_attributes = True


class IngestResponse(BaseModel):
    """Response schema for ingest operations."""
    document_id: uuid.UUID
    title: str
    status: DocumentStatus
    chunks_created: int
    message: str
