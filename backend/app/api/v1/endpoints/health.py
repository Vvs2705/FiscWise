"""
Health check endpoints for FiscWise.

This module provides health and readiness check endpoints for load balancers
and monitoring systems.
"""

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db


router = APIRouter()


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Health check",
    description="Basic health check endpoint for load balancers",
    tags=["Health"]
)
async def health_check():
    """
    Health check endpoint.
    
    Returns basic service information without checking dependencies.
    Used by load balancers for quick health verification.
    
    Returns:
        dict: Service status and version information
    """
    return {
        "status": "healthy",
        "service": "fiscwise-api",
        "version": "1.0.0"
    }


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Readiness check that verifies database connectivity",
    tags=["Health"]
)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    """
    Readiness check endpoint.
    
    Verifies that the service is ready to accept requests by checking
    database connectivity. Used by orchestrators (Kubernetes, Railway)
    to determine if the service should receive traffic.
    
    Args:
        db: Database session dependency
        
    Returns:
        dict: Readiness status with database connection state
    """
    try:
        # Test database connection
        await db.execute(text("SELECT 1"))
        
        return {
            "status": "ready",
            "database": "connected",
            "service": "fiscwise-api"
        }
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(e),
                "service": "fiscwise-api"
            }
        )


@router.get("/db-test", summary="Database Table Test")
async def db_test(db: AsyncSession = Depends(get_db)):
    """Test access to users table for diagnosing migration issues."""
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        count = result.scalar()
        return {"status": "success", "users_count": count}
    except Exception as e:
        return {"status": "error", "error": str(e), "error_type": type(e).__name__}
