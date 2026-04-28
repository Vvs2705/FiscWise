"""
Analytics schemas for ContaFlow.

This module defines Pydantic schemas for analytics and metrics responses.
"""

import uuid
from datetime import date, datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, ConfigDict


class TokenUsageByModel(BaseModel):
    """Token usage breakdown by AI model."""
    
    input_tokens: int = Field(..., description="Total input tokens for this model")
    output_tokens: int = Field(..., description="Total output tokens for this model")
    cost_usd: float = Field(..., description="Estimated cost in USD for this model")
    
    model_config = ConfigDict(from_attributes=True)


class TokenUsageByEndpoint(BaseModel):
    """Token usage breakdown by API endpoint."""
    
    input_tokens: int = Field(..., description="Total input tokens for this endpoint")
    output_tokens: int = Field(..., description="Total output tokens for this endpoint")
    
    model_config = ConfigDict(from_attributes=True)


class TokenUsageSummary(BaseModel):
    """Summary of token usage for a tenant."""
    
    total_input_tokens: int = Field(..., description="Total input tokens consumed")
    total_output_tokens: int = Field(..., description="Total output tokens generated")
    total_tokens: int = Field(..., description="Total tokens (input + output)")
    total_cost_usd: float = Field(..., description="Total estimated cost in USD")
    by_model: Dict[str, TokenUsageByModel] = Field(
        default_factory=dict,
        description="Token usage breakdown by AI model"
    )
    by_endpoint: Dict[str, TokenUsageByEndpoint] = Field(
        default_factory=dict,
        description="Token usage breakdown by API endpoint"
    )
    
    model_config = ConfigDict(from_attributes=True)


class SessionAnalytics(BaseModel):
    """Analytics for chat sessions."""
    
    total_sessions: int = Field(..., description="Total number of chat sessions")
    total_messages: int = Field(..., description="Total number of messages")
    avg_messages_per_session: float = Field(
        ...,
        description="Average number of messages per session"
    )
    
    model_config = ConfigDict(from_attributes=True)


class DocumentAnalytics(BaseModel):
    """Analytics for documents and chunks."""
    
    total_documents: int = Field(..., description="Total number of documents")
    total_chunks: int = Field(..., description="Total number of document chunks")
    avg_chunks_per_document: float = Field(
        ...,
        description="Average number of chunks per document"
    )
    by_status: Dict[str, int] = Field(
        default_factory=dict,
        description="Document count by status"
    )
    
    model_config = ConfigDict(from_attributes=True)


class DailyMetricsResponse(BaseModel):
    """Daily usage metrics response."""
    
    id: uuid.UUID = Field(..., description="Metrics record ID")
    tenant_id: uuid.UUID = Field(..., description="Tenant identifier")
    metric_date: date = Field(..., description="Date for which metrics are aggregated", alias="date")
    total_sessions: int = Field(..., description="Total sessions created on this date")
    total_messages: int = Field(..., description="Total messages sent on this date")
    total_input_tokens: int = Field(..., description="Total input tokens consumed")
    total_output_tokens: int = Field(..., description="Total output tokens generated")
    total_tokens: int = Field(..., description="Total tokens (input + output)")
    total_documents: int = Field(..., description="Total documents ingested")
    total_chunks: int = Field(..., description="Total chunks created")
    avg_messages_per_session: float = Field(
        ...,
        description="Average messages per session"
    )
    avg_chunks_per_document: float = Field(
        ...,
        description="Average chunks per document"
    )
    created_at: datetime = Field(..., description="Record creation timestamp")
    
    model_config = ConfigDict(from_attributes=True)


class DashboardData(BaseModel):
    """Aggregated data for dashboard display."""
    
    token_usage: TokenUsageSummary = Field(..., description="Token usage summary")
    sessions: SessionAnalytics = Field(..., description="Session analytics")
    documents: DocumentAnalytics = Field(..., description="Document analytics")
    daily_metrics: List[DailyMetricsResponse] = Field(
        default_factory=list,
        description="Daily metrics for the specified period"
    )
    
    model_config = ConfigDict(from_attributes=True)
