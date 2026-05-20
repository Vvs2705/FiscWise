"""
ContaFlow API - Main Application Entry Point

This module initializes the FastAPI application with all necessary
middleware, routers, and configuration.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging

from app.core.config import settings
from app.core.middleware import TenantMiddleware
from app.api.v1.api import api_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Initialize FastAPI application
app = FastAPI(
    title="ContaFlow API",
    description="Production-grade B2B SaaS platform for Brazilian accounting and financial services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Tenant Isolation Middleware
app.add_middleware(TenantMiddleware)

# Include API v1 routes
app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    Executes when the FastAPI application starts.
    """
    logger.info("ContaFlow API starting up...")
    logger.info("Environment: %s", settings.ENVIRONMENT)

    # Validate critical secrets and emit clear log lines for each.
    # These secrets must be set via: flyctl secrets set KEY=value
    missing_secrets: list[str] = []

    if not settings.DATABASE_URL:
        logger.critical(
            "[MISSING SECRET] DATABASE_URL is not set. "
            "DB-bound endpoints will fail until this secret is configured. "
            "Run: flyctl secrets set DATABASE_URL=<your-supabase-connection-string>"
        )
        missing_secrets.append("DATABASE_URL")
    else:
        logger.info("DATABASE_URL: %s...", settings.DATABASE_URL[:40])

    if not settings.JWT_SECRET_KEY:
        logger.critical(
            "[MISSING SECRET] JWT_SECRET_KEY is not set. "
            "All auth endpoints will fail until this secret is configured. "
            "Run: flyctl secrets set JWT_SECRET_KEY=$(openssl rand -hex 64)"
        )
        missing_secrets.append("JWT_SECRET_KEY")
    else:
        logger.info("JWT_SECRET_KEY: configured (length=%d)", len(settings.JWT_SECRET_KEY))

    if missing_secrets:
        logger.critical(
            "STARTUP WARNING: %d required secret(s) are missing: %s. "
            "The /api/v1/health endpoint is still healthy but DB/auth endpoints will return 500.",
            len(missing_secrets),
            ", ".join(missing_secrets),
        )
    else:
        logger.info("All required secrets are present.")

    logger.info("Application initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    Executes when the FastAPI application shuts down.
    """
    logger.info("ContaFlow API shutting down...")
    logger.info("Cleanup completed successfully")


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.
    
    Returns the operational status of the API.
    Used by load balancers and monitoring systems.
    
    Returns:
        dict: Status message indicating API is online
    """
    return JSONResponse(
        status_code=200,
        content={"status": "ContaFlow API Online"}
    )


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.
    
    Returns basic API information.
    
    Returns:
        dict: API name, version, and documentation links
    """
    return {
        "name": "ContaFlow API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
