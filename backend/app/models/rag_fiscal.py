"""SQLAlchemy models for RAG Fiscal Knowledge Base.
"""

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    DateTime, ForeignKey, String, Text, func,
    UUID as SQLUUID,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TenantBase


class RagDocument(Base, TenantBase):
    """
    Representa um documento ou procedimento na base de conhecimento RAG do escritório.
    """

    __tablename__ = "rag_documents"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Título do documento (ex: Manual do Simples, FAQ Interno)",
    )
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Conteúdo do documento para busca semântica",
    )
    source: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="Procedimento Interno",
        comment="Fonte do documento (ex: link, lei, manual)",
    )
    category: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="procedimento",
        index=True,
        comment="Categoria: regras_fiscais | manual | faq | procedimento",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
