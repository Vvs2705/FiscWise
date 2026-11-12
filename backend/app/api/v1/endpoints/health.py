"""
Health check endpoints for FiscWise.

This module provides health and readiness check endpoints for load balancers
and monitoring systems.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.endpoints.diagnostic import ensure_diagnostics_enabled
from app.core.deps import get_current_user, get_db
from app.models.user import User

logger = logging.getLogger(__name__)

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
    except Exception:
        # Detalhe do erro (host, usuário, driver) só no log — a rota é pública.
        logger.exception("Readiness: banco indisponível")
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={"status": "not_ready"},
        )


@router.get(
    "/db-test",
    summary="Database Table Test",
    dependencies=[Depends(ensure_diagnostics_enabled)],
)
async def db_test(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Diagnóstico de migration: conta usuários. 404 se DIAGNOSTICS_ENABLED=false.

    Antes era público e devolvia o texto da exceção do banco. Agora: atrás da
    flag, só owner autenticado, e erro detalhado vai só para o log.
    """
    if current_user.role.value != "owner":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Owner only")
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM users"))
        return {"status": "success", "users_count": result.scalar()}
    except Exception:
        logger.exception("db-test falhou")
        return {"status": "error"}
