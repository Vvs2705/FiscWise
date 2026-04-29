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
    logger.info("🚀 ContaFlow API starting up...")
    logger.info("📊 Environment: %s", settings.ENVIRONMENT)
    logger.info("✅ Application initialized successfully")


@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    Executes when the FastAPI application shuts down.
    """
    logger.info("🛑 ContaFlow API shutting down...")
    logger.info("✅ Cleanup completed successfully")


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
