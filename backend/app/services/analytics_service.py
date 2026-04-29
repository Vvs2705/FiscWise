"""
Analytics service for ContaFlow.

This module provides analytics and metrics aggregation functionality.
"""

import uuid
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import select, func, and_, cast, Date
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import DailyUsageMetrics
from app.models.chat import ChatSession, ChatMessage, TokenUsageLog
from app.models.knowledge import Document, DocumentChunk, DocumentStatus
from app.schemas.analytics import (
    TokenUsageSummary,
    TokenUsageByModel,
    TokenUsageByEndpoint,
    SessionAnalytics,
    DocumentAnalytics,
    DailyMetricsResponse,
    DashboardData,
)


# Claude 3.5 Haiku pricing (as of 2024)
# Source: https://www.anthropic.com/pricing
PRICING = {
    "claude-3-5-haiku-20241022": {
        "input": 0.00025,   # $0.25 per 1M tokens
        "output": 0.00125   # $1.25 per 1M tokens
    }
}


def calculate_cost(input_tokens: int, output_tokens: int, model: str) -> float:
    """
    Calculate estimated cost in USD for token usage.
    
    Args:
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        model: AI model name
        
    Returns:
        Estimated cost in USD
    """
    pricing = PRICING.get(model, {"input": 0, "output": 0})
    input_cost = (input_tokens / 1_000_000) * pricing["input"]
    output_cost = (output_tokens / 1_000_000) * pricing["output"]
    return round(input_cost + output_cost, 6)


class AnalyticsService:
    """Service for analytics and metrics aggregation."""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize analytics service.
        
        Args:
            db: Database session
        """
        self.db = db
    
    async def get_token_usage_summary(
        self,
        tenant_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> TokenUsageSummary:
        """
        Get token usage summary for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            
        Returns:
            Token usage summary with breakdown by model and endpoint
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()
        
        # Query token usage logs
        stmt = select(
            TokenUsageLog.model,
            TokenUsageLog.endpoint,
            func.sum(TokenUsageLog.input_tokens).label("total_input"),
            func.sum(TokenUsageLog.output_tokens).label("total_output")
        ).where(
            and_(
                TokenUsageLog.tenant_id == tenant_id,
                cast(TokenUsageLog.created_at, Date) >= start_date,
                cast(TokenUsageLog.created_at, Date) <= end_date
            )
        ).group_by(TokenUsageLog.model, TokenUsageLog.endpoint)
        
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        
        # Aggregate totals
        total_input = 0
        total_output = 0
        by_model: Dict[str, TokenUsageByModel] = {}
        by_endpoint: Dict[str, TokenUsageByEndpoint] = {}
        
        for row in rows:
            model, endpoint, input_tokens, output_tokens = row
            input_tokens = input_tokens or 0
            output_tokens = output_tokens or 0
            
            total_input += input_tokens
            total_output += output_tokens
            
            # Aggregate by model
            if model not in by_model:
                by_model[model] = TokenUsageByModel(
                    input_tokens=0,
                    output_tokens=0,
                    cost_usd=0.0
                )
            by_model[model].input_tokens += input_tokens
            by_model[model].output_tokens += output_tokens
            by_model[model].cost_usd = calculate_cost(
                by_model[model].input_tokens,
                by_model[model].output_tokens,
                model
            )
            
            # Aggregate by endpoint
            if endpoint not in by_endpoint:
                by_endpoint[endpoint] = TokenUsageByEndpoint(
                    input_tokens=0,
                    output_tokens=0
                )
            by_endpoint[endpoint].input_tokens += input_tokens
            by_endpoint[endpoint].output_tokens += output_tokens
        
        # Calculate total cost
        total_cost = sum(model_data.cost_usd for model_data in by_model.values())
        
        return TokenUsageSummary(
            total_input_tokens=total_input,
            total_output_tokens=total_output,
            total_tokens=total_input + total_output,
            total_cost_usd=total_cost,
            by_model=by_model,
            by_endpoint=by_endpoint
        )
    
    async def get_session_analytics(
        self,
        tenant_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> SessionAnalytics:
        """
        Get session analytics for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            start_date: Start date (default: 30 days ago)
            end_date: End date (default: today)
            
        Returns:
            Session analytics with totals and averages
        """
        if start_date is None:
            start_date = date.today() - timedelta(days=30)
        if end_date is None:
            end_date = date.today()
        
        # Query session and message counts
        stmt = select(
            func.count(func.distinct(ChatSession.id)).label("total_sessions"),
            func.count(ChatMessage.id).label("total_messages")
        ).select_from(ChatSession).outerjoin(
            ChatMessage,
            ChatMessage.session_id == ChatSession.id
        ).where(
            and_(
                ChatSession.tenant_id == tenant_id,
                cast(ChatSession.created_at, Date) >= start_date,
                cast(ChatSession.created_at, Date) <= end_date
            )
        )
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        
        total_sessions = row.total_sessions or 0
        total_messages = row.total_messages or 0
        
        # Calculate average
        avg_messages_per_session = 0.0
        if total_sessions > 0:
            avg_messages_per_session = round(total_messages / total_sessions, 2)
        
        return SessionAnalytics(
            total_sessions=total_sessions,
            total_messages=total_messages,
            avg_messages_per_session=avg_messages_per_session
        )
    
    async def get_document_analytics(
        self,
        tenant_id: uuid.UUID
    ) -> DocumentAnalytics:
        """
        Get document analytics for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Document analytics with totals and breakdown by status
        """
        # Query document and chunk counts
        stmt = select(
            func.count(func.distinct(Document.id)).label("total_documents"),
            func.count(DocumentChunk.id).label("total_chunks")
        ).select_from(Document).outerjoin(
            DocumentChunk,
            DocumentChunk.document_id == Document.id
        ).where(Document.tenant_id == tenant_id)
        
        result = await self.db.execute(stmt)
        row = result.fetchone()
        
        total_documents = row.total_documents or 0
        total_chunks = row.total_chunks or 0
        
        # Calculate average
        avg_chunks_per_document = 0.0
        if total_documents > 0:
            avg_chunks_per_document = round(total_chunks / total_documents, 2)
        
        # Query document count by status
        stmt_status = select(
            Document.status,
            func.count(Document.id).label("count")
        ).where(
            Document.tenant_id == tenant_id
        ).group_by(Document.status)
        
        result_status = await self.db.execute(stmt_status)
        rows_status = result_status.fetchall()
        
        by_status = {row.status.value: row.count for row in rows_status}
        
        return DocumentAnalytics(
            total_documents=total_documents,
            total_chunks=total_chunks,
            avg_chunks_per_document=avg_chunks_per_document,
            by_status=by_status
        )
    
    async def get_daily_metrics(
        self,
        tenant_id: uuid.UUID,
        days: int = 30
    ) -> List[DailyMetricsResponse]:
        """
        Get daily metrics for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            days: Number of days to retrieve (default: 30)
            
        Returns:
            List of daily metrics ordered by date (oldest first)
        """
        start_date = date.today() - timedelta(days=days - 1)
        
        stmt = select(DailyUsageMetrics).where(
            and_(
                DailyUsageMetrics.tenant_id == tenant_id,
                DailyUsageMetrics.date >= start_date
            )
        ).order_by(DailyUsageMetrics.date.asc())
        
        result = await self.db.execute(stmt)
        metrics = result.scalars().all()
        
        return [
            DailyMetricsResponse(
                id=m.id,
                tenant_id=m.tenant_id,
                date=m.date,
                total_sessions=m.total_sessions,
                total_messages=m.total_messages,
                total_input_tokens=m.total_input_tokens,
                total_output_tokens=m.total_output_tokens,
                total_tokens=m.total_tokens,
                total_documents=m.total_documents,
                total_chunks=m.total_chunks,
                avg_messages_per_session=m.avg_messages_per_session,
                avg_chunks_per_document=m.avg_chunks_per_document,
                created_at=m.created_at
            )
            for m in metrics
        ]
    
    async def aggregate_daily_metrics(
        self,
        tenant_id: uuid.UUID,
        target_date: date
    ) -> DailyUsageMetrics:
        """
        Aggregate metrics for a specific date.
        
        This method calculates and stores daily metrics for a tenant.
        If metrics already exist for the date, they are updated (upsert).
        
        Args:
            tenant_id: Tenant identifier
            target_date: Date to aggregate metrics for
            
        Returns:
            Aggregated daily metrics
        """
        # Query session count
        stmt_sessions = select(
            func.count(ChatSession.id).label("total_sessions")
        ).where(
            and_(
                ChatSession.tenant_id == tenant_id,
                cast(ChatSession.created_at, Date) == target_date
            )
        )
        result_sessions = await self.db.execute(stmt_sessions)
        total_sessions = result_sessions.scalar() or 0
        
        # Query message count
        stmt_messages = select(
            func.count(ChatMessage.id).label("total_messages")
        ).select_from(ChatMessage).join(
            ChatSession,
            ChatMessage.session_id == ChatSession.id
        ).where(
            and_(
                ChatSession.tenant_id == tenant_id,
                cast(ChatMessage.created_at, Date) == target_date
            )
        )
        result_messages = await self.db.execute(stmt_messages)
        total_messages = result_messages.scalar() or 0
        
        # Query token usage
        stmt_tokens = select(
            func.sum(TokenUsageLog.input_tokens).label("total_input"),
            func.sum(TokenUsageLog.output_tokens).label("total_output")
        ).where(
            and_(
                TokenUsageLog.tenant_id == tenant_id,
                cast(TokenUsageLog.created_at, Date) == target_date
            )
        )
        result_tokens = await self.db.execute(stmt_tokens)
        row_tokens = result_tokens.fetchone()
        total_input_tokens = row_tokens.total_input or 0
        total_output_tokens = row_tokens.total_output or 0
        
        # Query document count
        stmt_documents = select(
            func.count(Document.id).label("total_documents")
        ).where(
            and_(
                Document.tenant_id == tenant_id,
                cast(Document.created_at, Date) == target_date
            )
        )
        result_documents = await self.db.execute(stmt_documents)
        total_documents = result_documents.scalar() or 0
        
        # Query chunk count
        stmt_chunks = select(
            func.count(DocumentChunk.id).label("total_chunks")
        ).select_from(DocumentChunk).join(
            Document,
            DocumentChunk.document_id == Document.id
        ).where(
            and_(
                Document.tenant_id == tenant_id,
                cast(DocumentChunk.created_at, Date) == target_date
            )
        )
        result_chunks = await self.db.execute(stmt_chunks)
        total_chunks = result_chunks.scalar() or 0
        
        # Check if metrics already exist
        stmt_existing = select(DailyUsageMetrics).where(
            and_(
                DailyUsageMetrics.tenant_id == tenant_id,
                DailyUsageMetrics.date == target_date
            )
        )
        result_existing = await self.db.execute(stmt_existing)
        existing_metrics = result_existing.scalar_one_or_none()
        
        if existing_metrics:
            # Update existing metrics
            existing_metrics.total_sessions = total_sessions
            existing_metrics.total_messages = total_messages
            existing_metrics.total_input_tokens = total_input_tokens
            existing_metrics.total_output_tokens = total_output_tokens
            existing_metrics.total_documents = total_documents
            existing_metrics.total_chunks = total_chunks
            existing_metrics.updated_at = datetime.now()
            await self.db.commit()
            await self.db.refresh(existing_metrics)
            return existing_metrics
        else:
            # Create new metrics
            new_metrics = DailyUsageMetrics(
                id=uuid.uuid4(),
                tenant_id=tenant_id,
                date=target_date,
                total_sessions=total_sessions,
                total_messages=total_messages,
                total_input_tokens=total_input_tokens,
                total_output_tokens=total_output_tokens,
                total_documents=total_documents,
                total_chunks=total_chunks
            )
            self.db.add(new_metrics)
            await self.db.commit()
            await self.db.refresh(new_metrics)
            return new_metrics
    
    async def get_dashboard_data(
        self,
        tenant_id: uuid.UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        days: int = 30
    ) -> DashboardData:
        """
        Get aggregated dashboard data for a tenant.
        
        Args:
            tenant_id: Tenant identifier
            start_date: Start date for token/session analytics (default: 30 days ago)
            end_date: End date for token/session analytics (default: today)
            days: Number of days for daily metrics (default: 30)
            
        Returns:
            Complete dashboard data with all analytics
        """
        # Get all analytics in parallel would be ideal, but for simplicity we'll do sequential
        token_usage = await self.get_token_usage_summary(tenant_id, start_date, end_date)
        sessions = await self.get_session_analytics(tenant_id, start_date, end_date)
        documents = await self.get_document_analytics(tenant_id)
        daily_metrics = await self.get_daily_metrics(tenant_id, days)
        
        return DashboardData(
            token_usage=token_usage,
            sessions=sessions,
            documents=documents,
            daily_metrics=daily_metrics
        )
