"""
API v1 Router for ContaFlow

Aggregates all v1 endpoint routers into a single API router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, onboarding, health, operations, diagnostic


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

# Include CTFlow operational MVP endpoints
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
