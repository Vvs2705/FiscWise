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
    DATABASE_URL: str = "postgresql+asyncpg://contaflow:contaflow_dev_2026@postgres:5432/contaflow_db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str) -> str:
        """Ensure DATABASE_URL uses the asyncpg driver required by SQLAlchemy async."""
        if isinstance(v, str):
            if v.startswith("postgres://"):
                return v.replace("postgres://", "postgresql+asyncpg://", 1)
            if v.startswith("postgresql://") and "+asyncpg" not in v:
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v
    
    # Redis
    REDIS_URL: str = "redis://:contaflow_redis_2026@redis:6379/0"
    
    # JWT Authentication
    JWT_SECRET_KEY: str = "contaflow_dev_secret_key_2026_do_not_use_in_production_generate_with_openssl_rand_hex_64"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Ensure JWT_SECRET_KEY is not using development default in production."""
        environment = info.data.get("ENVIRONMENT", "development")
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
    
    # AI Services
    ANTHROPIC_API_KEY: str = ""
    VOYAGE_API_KEY: str = ""
    
    @field_validator("ANTHROPIC_API_KEY", "VOYAGE_API_KEY", mode="before")
    @classmethod
    def validate_ai_keys(cls, v: str, info) -> str:
        """Ensure AI API keys are provided in production."""
        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and not v:
            raise ValueError(
                "AI service API keys (ANTHROPIC_API_KEY, VOYAGE_API_KEY) "
                "must be set in production environment."
            )
        return v
    
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
