"""
Chat Schemas for ContaFlow

Pydantic models for chat-related request/response validation.
"""
import uuid
from datetime import datetime
from pydantic import BaseModel
from typing import Optional


class CreateSessionRequest(BaseModel):
    """Request schema for creating a new chat session."""
    title: Optional[str] = "Nova conversa"


class SessionResponse(BaseModel):
    """Response schema for chat session data."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    title: str
    message_count: int
    created_at: datetime
    
    class Config:
        from_attributes = True


class ChatMessageRequest(BaseModel):
    """Request schema for sending a chat message."""
    message: str


class MessageResponse(BaseModel):
    """Response schema for chat message data."""
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    tokens_used: int
    created_at: datetime
    
    class Config:
        from_attributes = True
