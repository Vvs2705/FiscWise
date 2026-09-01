"""
API v1 Router for FiscWise

Aggregates all v1 endpoint routers into a single API router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, onboarding, health, operations, diagnostic, admin, calculator


# Create main API router for v1
api_router = APIRouter()

# Include authentication endpoints
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"]
)

# Include onboarding endpoints
api_router.include_router(
    onboarding.router,
    prefix="/onboarding",
    tags=["Onboarding"]
)

# Include health check endpoints
api_router.include_router(
    health.router,
    tags=["Health"]
)

# Include FiscWise operational MVP endpoints
api_router.include_router(
    operations.router,
    tags=["Operations"]
)

# Include diagnostic endpoints (for debugging)
api_router.include_router(
    diagnostic.router,
    prefix="/diagnostic",
    tags=["Diagnostic"]
)

# Include admin endpoints (emergency fixes)
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Admin"]
)

# Include Feature #7 — Calculadora Fiscal com IA
api_router.include_router(
    calculator.router,
    prefix="/calculator",
    tags=["Calculator"]
)
