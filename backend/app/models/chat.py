"""
Chat Models for ContaFlow

Defines ChatSession, ChatMessage, and TokenUsageLog models for the chat system.
Supports multi-turn conversations with RAG context and token usage tracking.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Text, Integer, DateTime, UUID as SQLUUID, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class ChatSession(Base, TenantBase):
    """
    Chat session model for multi-turn conversations.
    
    Represents a conversation session between a user and the AI assistant.
    Inherits tenant isolation from TenantBase.
    
    Attributes:
        id: Primary key UUID (inherited from TenantBase)
        tenant_id: Foreign key to tenants table (inherited from TenantBase)
        title: Session title or name
        message_count: Number of messages in this session
        created_at: Session creation timestamp (inherited from TenantBase)
        updated_at: Last update timestamp (inherited from TenantBase)
        messages: Relationship to ChatMessage model (one-to-many)
    """
    
    __tablename__ = "chat_sessions"
    
    # Session Metadata
    title: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        default="Nova conversa",
        comment="Session title or name"
    )
    
    message_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of messages in this session"
    )
    
    # Relationships
    messages: Mapped[list["ChatMessage"]] = relationship(
        "ChatMessage",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        """String representation of the chat session."""
        return f"<ChatSession(id={self.id}, title='{self.title}', message_count={self.message_count}, tenant_id={self.tenant_id})>"


class ChatMessage(Base):
    """
    Chat message model for individual messages within a session.
    
    Represents a single message (user or assistant) in a conversation.
    Inherits tenant isolation through the session_id foreign key relationship.
    
    Attributes:
        id: Primary key UUID
        session_id: Foreign key to chat_sessions table
        role: Message role (user or assistant)
        content: Message text content
        tokens_used: Number of tokens used for this message
        created_at: Message creation timestamp
        session: Relationship to ChatSession model (many-to-one)
    """
    
    __tablename__ = "chat_messages"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Message unique identifier"
    )
    
    # Foreign Key to ChatSession
    session_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("chat_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to parent chat session"
    )
    
    # Message Content
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Message role: user or assistant"
    )
    
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Message text content"
    )
    
    tokens_used: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Number of tokens used for this message"
    )
    
    # Audit Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Message creation timestamp"
    )
    
    # Relationships
    session: Mapped["ChatSession"] = relationship(
        "ChatSession",
        back_populates="messages"
    )
    
    def __repr__(self) -> str:
        """String representation of the chat message."""
        return f"<ChatMessage(id={self.id}, role='{self.role}', session_id={self.session_id})>"


class TokenUsageLog(Base, TenantBase):
    """
    Token usage log model for tracking AI API consumption.
    
    Tracks token usage for billing and analytics purposes.
    Inherits tenant isolation from TenantBase.
    
    Attributes:
        id: Primary key UUID (inherited from TenantBase)
        tenant_id: Foreign key to tenants table (inherited from TenantBase)
        input_tokens: Number of input tokens consumed
        output_tokens: Number of output tokens generated
        model: AI model used (e.g., claude-3-5-haiku-20241022)
        endpoint: API endpoint that generated the usage (e.g., chat, completion)
        created_at: Log creation timestamp (inherited from TenantBase)
    """
    
    __tablename__ = "token_usage_logs"
    
    # Token Usage
    input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of input tokens consumed"
    )
    
    output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="Number of output tokens generated"
    )
    
    # Model Information
    model: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="AI model used (e.g., claude-3-5-haiku-20241022)"
    )
    
    endpoint: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="API endpoint that generated the usage"
    )
    
    def __repr__(self) -> str:
        """String representation of the token usage log."""
        return f"<TokenUsageLog(id={self.id}, model='{self.model}', input={self.input_tokens}, output={self.output_tokens}, tenant_id={self.tenant_id})>"
    
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens used."""
        return self.input_tokens + self.output_tokens
