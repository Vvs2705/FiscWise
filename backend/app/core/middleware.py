"""
Middleware Module for ContaFlow

Custom middleware for tenant isolation and request processing.
Enforces X-Tenant-ID header on protected routes.
"""

import uuid
from typing import Set

from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


# Routes that don't require tenant isolation
_EXCLUDED_PREFIXES: Set[str] = {
    "/health",
    "/api/v1/health",
    "/api/v1/db-test",       # Database diagnostic endpoint
    "/api/v1/diagnostic",    # Diagnostic endpoints (debugging)
    "/api/v1/widget",        # Public embeddable widget (no auth required)
    "/docs",
    "/redoc",
    "/openapi.json",
    "/api/v1/auth",
    "/api/v1/onboarding",
}

_EXCLUDED_EXACT_PATHS: Set[str] = {"/"}


class TenantMiddleware(BaseHTTPMiddleware):
    """
    Middleware to enforce tenant isolation via X-Tenant-ID header.
    
    For all routes except public endpoints (auth, docs, health),
    this middleware requires the X-Tenant-ID header to be present.
    
    Excluded routes (public access):
        - /health (health check)
        - /docs, /redoc, /openapi.json (API documentation)
        - /api/v1/auth/* (authentication endpoints)
        - /api/v1/onboarding/* (tenant registration)
        - / (root endpoint)
    
    For protected routes:
        - Validates presence of X-Tenant-ID header
        - Returns 400 Bad Request if header is missing
        - Attaches tenant_id to request.state for downstream use
    """
    
    async def dispatch(self, request: Request, call_next):
        """
        Process each request and enforce tenant isolation.
        
        Args:
            request: The incoming HTTP request
            call_next: The next middleware or route handler
            
        Returns:
            Response from the next handler or error response
        """
        path = request.url.path
        
        is_excluded = path in _EXCLUDED_EXACT_PATHS or any(
            path == prefix or path.startswith(f"{prefix}/")
            for prefix in _EXCLUDED_PREFIXES
        )
        
        if is_excluded:
            # Allow public routes to pass through without tenant validation
            return await call_next(request)
        
        # Protected route: require X-Tenant-ID header
        tenant_id = request.headers.get("X-Tenant-ID")
        
        if not tenant_id:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Missing required header: X-Tenant-ID",
                    "error_code": "TENANT_ID_REQUIRED",
                    "message": "All protected endpoints require the X-Tenant-ID header for tenant isolation"
                }
            )

        try:
            uuid.UUID(tenant_id)
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": "Invalid X-Tenant-ID header",
                    "error_code": "TENANT_ID_INVALID",
                    "message": "X-Tenant-ID must be a valid UUID"
                }
            )
        
        # Attach tenant_id to request state for use in route handlers
        request.state.tenant_id = tenant_id
        
        # Continue to next middleware or route handler
        response = await call_next(request)
        return response
