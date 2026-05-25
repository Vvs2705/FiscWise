"""Pydantic schemas for RAG Fiscal Knowledge Base.
"""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RagDocumentCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    content: str = Field(..., min_length=10)
    source: str = Field(default="Procedimento Interno", max_length=255)
    category: str = Field(default="procedimento", max_length=50)


class RagDocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    content: Optional[str] = Field(None, min_length=10)
    source: Optional[str] = Field(None, max_length=255)
    category: Optional[str] = Field(None, max_length=50)


class RagDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    content: str
    source: str
    category: str
    created_at: datetime
    updated_at: datetime
