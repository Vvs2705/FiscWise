"""
FiscWise API - Main Application Entry Point

This module initializes the FastAPI application with all necessary
middleware, routers, and configuration.
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.core.config import settings
from app.core.middleware import TenantMiddleware
from app.core.rate_limit import RateLimitMiddleware
from app.api.v1.api import api_router
from app.services.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.ENVIRONMENT,
        release=f"fiscwise-api@{settings.APP_VERSION}",
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,
        profiles_sample_rate=settings.SENTRY_PROFILES_SAMPLE_RATE,
        integrations=[
            FastApiIntegration(),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            SqlalchemyIntegration(),
        ],
        send_default_pii=False,
    )
    logger.info("Sentry initialized for backend environment=%s", settings.ENVIRONMENT)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan context manager.

    Handles startup validation and graceful shutdown.
    Replaces the deprecated @app.on_event("startup") / @app.on_event("shutdown").
    """
    # ── Startup ──────────────────────────────────────────────────────────────
    logger.info("FiscWise API starting up...")
    logger.info("Environment: %s", settings.ENVIRONMENT)

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

    # Start background scheduler for tasks like monthly billing
    await start_scheduler()

    yield  # Application runs here

    # ── Shutdown ──────────────────────────────────────────────────────────────
    logger.info("FiscWise API shutting down...")
    await stop_scheduler()
    logger.info("Cleanup completed successfully")


# Initialize FastAPI application
app = FastAPI(
    title="FiscWise API",
    description="Production-grade B2B SaaS platform for Brazilian accounting and financial services",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
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

# Rate limiting middleware. In strict mode, protected routes fail closed without Redis.
app.add_middleware(RateLimitMiddleware, redis_url=settings.REDIS_URL or None)

# Include API v1 routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Health check endpoint.

    Returns the operational status of the API.
    Used by load balancers and monitoring systems.
    """
    return JSONResponse(
        status_code=200,
        content={"status": "FiscWise API Online"}
    )


@app.get("/", tags=["Root"])
async def root():
    """
    Root endpoint.

    Returns basic API information.
    """
    return {
        "name": "FiscWise API",
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
