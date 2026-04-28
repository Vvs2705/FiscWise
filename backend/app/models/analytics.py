"""
Analytics models for ContaFlow.

This module defines models for storing aggregated metrics and analytics data.
"""

import uuid
from datetime import datetime, date
from typing import Optional

from sqlalchemy import String, Integer, Date, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, TenantBase


class DailyUsageMetrics(Base, TenantBase):
    """
    Daily aggregated usage metrics per tenant.
    
    This model stores pre-calculated daily metrics for performance optimization.
    Metrics are aggregated by a background task or on-demand.
    """
    
    __tablename__ = "daily_usage_metrics"
    
    # Date for which metrics are aggregated
    date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
        comment="Date for which metrics are aggregated"
    )
    
    # Session metrics
    total_sessions: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total chat sessions created on this date"
    )
    
    total_messages: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total chat messages sent on this date"
    )
    
    # Token usage metrics
    total_input_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total input tokens consumed on this date"
    )
    
    total_output_tokens: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total output tokens generated on this date"
    )
    
    # Document metrics
    total_documents: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total documents ingested on this date"
    )
    
    total_chunks: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Total document chunks created on this date"
    )
    
    # Unique constraint: one record per tenant per date
    __table_args__ = (
        UniqueConstraint('tenant_id', 'date', name='uq_daily_metrics_tenant_date'),
        Index('ix_daily_usage_metrics_tenant_date', 'tenant_id', 'date'),
    )
    
    @property
    def total_tokens(self) -> int:
        """Calculate total tokens (input + output)."""
        return self.total_input_tokens + self.total_output_tokens
    
    @property
    def avg_messages_per_session(self) -> float:
        """Calculate average messages per session."""
        if self.total_sessions == 0:
            return 0.0
        return round(self.total_messages / self.total_sessions, 2)
    
    @property
    def avg_chunks_per_document(self) -> float:
        """Calculate average chunks per document."""
        if self.total_documents == 0:
            return 0.0
        return round(self.total_chunks / self.total_documents, 2)
    
    def __repr__(self) -> str:
        return (
            f"<DailyUsageMetrics(id={self.id}, tenant_id={self.tenant_id}, "
            f"date={self.date}, sessions={self.total_sessions}, "
            f"messages={self.total_messages}, tokens={self.total_tokens})>"
        )
