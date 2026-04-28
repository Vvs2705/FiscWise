"""
Knowledge Base Models for ContaFlow

Defines Document and DocumentChunk models for RAG (Retrieval-Augmented Generation).
Uses pgvector for semantic search capabilities with 1536-dimensional embeddings.
"""

import uuid
from datetime import datetime
from typing import Optional
import enum

from sqlalchemy import String, Text, DateTime, UUID as SQLUUID, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector

from app.models.base import Base, TenantBase


class DocumentStatus(str, enum.Enum):
    """
    Document processing status enumeration.
    
    Tracks the lifecycle of document processing for RAG pipeline.
    """
    PENDING = "pending"
    PROCESSING = "processing"
    PROCESSED = "processed"
    FAILED = "failed"


class Document(Base, TenantBase):
    """
    Document model for knowledge base.
    
    Represents a source document that will be chunked and embedded
    for semantic search and RAG capabilities.
    
    Attributes:
        id: Primary key UUID (inherited from TenantBase)
        tenant_id: Foreign key to tenants table (inherited from TenantBase)
        title: Document title or name
        content_type: Type of content (text, pdf, url, etc.)
        status: Processing status (pending/processing/processed/failed)
        created_at: Document creation timestamp (inherited from TenantBase)
        updated_at: Last update timestamp (inherited from TenantBase)
        chunks: Relationship to DocumentChunk model (one-to-many)
    """
    
    __tablename__ = "documents"
    
    # Document Metadata
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Document title or name"
    )
    
    content_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="Content type: text, pdf, url, docx, etc."
    )
    
    # Processing Status
    status: Mapped[DocumentStatus] = mapped_column(
        SQLEnum(DocumentStatus, name="document_status_enum", create_type=True),
        nullable=False,
        default=DocumentStatus.PENDING,
        index=True,
        comment="Document processing status"
    )
    
    # Relationships
    chunks: Mapped[list["DocumentChunk"]] = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        """String representation of the document."""
        return f"<Document(id={self.id}, title='{self.title}', status={self.status.value}, tenant_id={self.tenant_id})>"
    
    def is_processed(self) -> bool:
        """Check if document has been successfully processed."""
        return self.status == DocumentStatus.PROCESSED


class DocumentChunk(Base):
    """
    Document chunk model for vector embeddings.
    
    Represents a chunk of a document with its vector embedding for semantic search.
    Inherits tenant isolation through the document_id foreign key relationship.
    
    Attributes:
        id: Primary key UUID
        document_id: Foreign key to documents table
        content: Text content of the chunk
        embedding: Vector embedding (1536 dimensions for OpenAI ada-002)
        created_at: Chunk creation timestamp
        updated_at: Last update timestamp
        document: Relationship to Document model (many-to-one)
    """
    
    __tablename__ = "document_chunks"
    
    # Primary Key
    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Chunk unique identifier"
    )
    
    # Foreign Key to Document
    document_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to parent document"
    )
    
    # Chunk Content
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Text content of the chunk"
    )
    
    # Vector Embedding (1024 dimensions - Voyage AI voyage-2)
    embedding: Mapped[Optional[Vector]] = mapped_column(
        Vector(1024),
        nullable=True,
        comment="Vector embedding for semantic search (1024 dimensions - Voyage AI voyage-2)"
    )
    
    # Audit Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Chunk creation timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Chunk last update timestamp"
    )
    
    # Relationships
    document: Mapped["Document"] = relationship(
        "Document",
        back_populates="chunks",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        """String representation of the chunk."""
        content_preview = self.content[:50] + "..." if len(self.content) > 50 else self.content
        return f"<DocumentChunk(id={self.id}, document_id={self.document_id}, content='{content_preview}')>"
    
    def has_embedding(self) -> bool:
        """Check if chunk has an embedding vector."""
        return self.embedding is not None
