"""
Configuration Module for ContaFlow

Centralized configuration management using Pydantic Settings.
Loads environment variables and provides type-safe configuration access.
"""

import os
from typing import List

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Uses Pydantic Settings for validation and type safety.
    """
    
    # Application
    APP_NAME: str = "ContaFlow"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    ENVIRONMENT: str = "development"
    
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://contaflow:contaflow_dev_2026@postgres:5432/contaflow_db"
    
    # Redis
    REDIS_URL: str = "redis://:contaflow_redis_2026@redis:6379/0"
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "your-secret-key-here-generate-with-openssl-rand-hex-64"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"
    
    # AI Services
    ANTHROPIC_API_KEY: str = ""
    VOYAGE_API_KEY: str = ""
    
    # RAG Config
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RESULTS: int = 5
    EMBEDDING_DIMENSIONS: int = 1024
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
