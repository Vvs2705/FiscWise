"""
Analytics API endpoints for ContaFlow.

This module provides REST endpoints for analytics and metrics.
"""

import uuid
from datetime import date, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services.analytics_service import AnalyticsService
from app.schemas.analytics import (
    TokenUsageSummary,
    SessionAnalytics,
    DocumentAnalytics,
    DailyMetricsResponse,
    DashboardData,
)


router = APIRouter()


@router.get(
    "/token-usage",
    response_model=TokenUsageSummary,
    summary="Get token usage summary",
    description="Get token usage summary with breakdown by model and endpoint"
)
async def get_token_usage(
    start_date: Optional[date] = Query(
        None,
        description="Start date (default: 30 days ago)"
    ),
    end_date: Optional[date] = Query(
        None,
        description="End date (default: today)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> TokenUsageSummary:
    """
    Get token usage summary for the authenticated tenant.
    
    Returns:
    - Total input/output tokens
    - Estimated cost in USD
    - Breakdown by AI model
    - Breakdown by API endpoint
    """
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_token_usage_summary(
        tenant_id=current_user.tenant_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get(
    "/sessions",
    response_model=SessionAnalytics,
    summary="Get session analytics",
    description="Get chat session statistics and metrics"
)
async def get_session_analytics(
    start_date: Optional[date] = Query(
        None,
        description="Start date (default: 30 days ago)"
    ),
    end_date: Optional[date] = Query(
        None,
        description="End date (default: today)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> SessionAnalytics:
    """
    Get session analytics for the authenticated tenant.
    
    Returns:
    - Total number of sessions
    - Total number of messages
    - Average messages per session
    """
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_session_analytics(
        tenant_id=current_user.tenant_id,
        start_date=start_date,
        end_date=end_date
    )


@router.get(
    "/documents",
    response_model=DocumentAnalytics,
    summary="Get document analytics",
    description="Get document and chunk statistics"
)
async def get_document_analytics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DocumentAnalytics:
    """
    Get document analytics for the authenticated tenant.
    
    Returns:
    - Total number of documents
    - Total number of chunks
    - Average chunks per document
    - Document count by status
    """
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_document_analytics(
        tenant_id=current_user.tenant_id
    )


@router.get(
    "/daily-metrics",
    response_model=List[DailyMetricsResponse],
    summary="Get daily metrics",
    description="Get daily aggregated metrics for the specified period"
)
async def get_daily_metrics(
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Number of days to retrieve (1-365)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> List[DailyMetricsResponse]:
    """
    Get daily metrics for the authenticated tenant.
    
    Returns list of daily metrics ordered by date (oldest first).
    Each metric includes:
    - Session and message counts
    - Token usage
    - Document and chunk counts
    - Calculated averages
    """
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_daily_metrics(
        tenant_id=current_user.tenant_id,
        days=days
    )


@router.get(
    "/dashboard",
    response_model=DashboardData,
    summary="Get dashboard data",
    description="Get complete aggregated data for dashboard display"
)
async def get_dashboard_data(
    start_date: Optional[date] = Query(
        None,
        description="Start date for token/session analytics (default: 30 days ago)"
    ),
    end_date: Optional[date] = Query(
        None,
        description="End date for token/session analytics (default: today)"
    ),
    days: int = Query(
        30,
        ge=1,
        le=365,
        description="Number of days for daily metrics (1-365)"
    ),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DashboardData:
    """
    Get complete dashboard data for the authenticated tenant.
    
    This endpoint aggregates all analytics into a single response:
    - Token usage summary with cost breakdown
    - Session analytics
    - Document analytics
    - Daily metrics for charts
    
    Optimized for dashboard UI rendering.
    """
    analytics_service = AnalyticsService(db)
    return await analytics_service.get_dashboard_data(
        tenant_id=current_user.tenant_id,
        start_date=start_date,
        end_date=end_date,
        days=days
    )


@router.post(
    "/aggregate/{target_date}",
    response_model=DailyMetricsResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Aggregate daily metrics",
    description="Manually trigger aggregation of metrics for a specific date"
)
async def aggregate_daily_metrics(
    target_date: date,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> DailyMetricsResponse:
    """
    Aggregate metrics for a specific date.
    
    This endpoint allows manual triggering of daily metrics aggregation.
    Useful for:
    - Backfilling historical data
    - Refreshing metrics after data corrections
    - Testing aggregation logic
    
    If metrics already exist for the date, they will be updated (upsert).
    """
    analytics_service = AnalyticsService(db)
    metrics = await analytics_service.aggregate_daily_metrics(
        tenant_id=current_user.tenant_id,
        target_date=target_date
    )
    
    return DailyMetricsResponse(
        id=metrics.id,
        tenant_id=metrics.tenant_id,
        date=metrics.date,
        total_sessions=metrics.total_sessions,
        total_messages=metrics.total_messages,
        total_input_tokens=metrics.total_input_tokens,
        total_output_tokens=metrics.total_output_tokens,
        total_tokens=metrics.total_tokens,
        total_documents=metrics.total_documents,
        total_chunks=metrics.total_chunks,
        avg_messages_per_session=metrics.avg_messages_per_session,
        avg_chunks_per_document=metrics.avg_chunks_per_document,
        created_at=metrics.created_at
    )
