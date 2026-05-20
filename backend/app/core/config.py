"""
Configuration Module for ContaFlow

Centralized configuration management using Pydantic Settings.
Loads environment variables and provides type-safe configuration access.
"""

import os
from typing import List

from pydantic import field_validator, ConfigDict
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
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str, info) -> str:
        """Ensure DATABASE_URL is set and uses the asyncpg driver."""
        if not v:
            environment = info.data.get("ENVIRONMENT", "development")
            if environment == "production":
                raise ValueError("DATABASE_URL must be set via environment variable in production.")
            # Dev default only if not in production
            return "postgresql+asyncpg://contaflow:dev_password@localhost:5432/contaflow_db"

        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Redis
    REDIS_URL: str = ""

    @field_validator("REDIS_URL", mode="before")
    @classmethod
    def validate_redis_url(cls, v: str, info) -> str:
        """Ensure REDIS_URL is set in production."""
        if not v:
            environment = info.data.get("ENVIRONMENT", "development")
            if environment == "production":
                raise ValueError("REDIS_URL must be set via environment variable in production.")
            # Dev default only if not in production
            return "redis://localhost:6379/0"
        return v
    
    # JWT Authentication
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Ensure JWT_SECRET_KEY is set securely."""
        if not v:
            environment = info.data.get("ENVIRONMENT", "development")
            if environment == "production":
                raise ValueError(
                    "JWT_SECRET_KEY must be set via environment variable in production. "
                    "Generate a secure key using: openssl rand -hex 64"
                )
            # Dev default only if not in production
            return "dev_secret_key_do_not_use_in_production_change_in_railway"

        if environment := info.data.get("ENVIRONMENT", "development"):
            if environment == "production" and "dev_secret" in v.lower():
                raise ValueError(
                    "JWT_SECRET_KEY must not use development default in production. "
                    "Generate a secure key using: openssl rand -hex 64"
                )
        return v
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Public URL (used for widget script generation)
    PUBLIC_URL: str = "https://api.contabilidadeflow.com.br"
    
    # AI Services (optional — RAG engine removed in Phase 5)
    ANTHROPIC_API_KEY: str = ""
    VOYAGE_API_KEY: str = ""
    
    @field_validator("DEBUG", mode="before")
    @classmethod
    def validate_debug_mode(cls, v, info) -> bool:
        """Ensure DEBUG is False in production."""
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and v is True:
            raise ValueError("DEBUG must be False in production environment.")
        return v
    
    # RAG Config
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 200
    TOP_K_RESULTS: int = 5
    EMBEDDING_DIMENSIONS: int = 1024
    
    @property
    def allowed_origins_list(self) -> List[str]:
        """Parse ALLOWED_ORIGINS into a list."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]
    
    model_config = ConfigDict(
        env_file=".env",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings instance
settings = Settings()
