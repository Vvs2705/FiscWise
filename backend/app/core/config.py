"""
Configuration Module for FiscWise

Centralized configuration management using Pydantic Settings.
Loads environment variables and provides type-safe configuration access.
"""

import os
from typing import List
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from pydantic import field_validator, ConfigDict
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.

    Uses Pydantic Settings for validation and type safety.
    """

    # Application
    # IMPORTANT: ENVIRONMENT must be declared FIRST — Pydantic v2 populates
    # info.data with fields validated so far (in declaration order).  Any
    # field whose @field_validator reads info.data.get("ENVIRONMENT") must be
    # declared AFTER this line so that ENVIRONMENT is already in info.data
    # when those validators run.
    ENVIRONMENT: str = "development"

    APP_NAME: str = "FiscWise"
    APP_VERSION: str = "1.0.0"

    # DEBUG defaults to False so that a missing DEBUG env var in production
    # never causes a startup crash.  The validator below overrides to False
    # whenever ENVIRONMENT=production, regardless of the value supplied.
    DEBUG: bool = False

    # Database
    DATABASE_URL: str = ""

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def fix_database_url(cls, v: str, info) -> str:
        """Ensure DATABASE_URL uses the asyncpg driver and remove sslmode param.

        Supabase URLs include sslmode parameter which asyncpg doesn't support.
        In production the value MUST be provided via Fly.io secrets.
        We intentionally do NOT raise here if the value is missing so
        that the process can start and the /api/v1/health endpoint (which
        does NOT touch the database) can respond to the Fly.io health-
        check while migrations are still running.  The database engine is
        created lazily (deps.py) so a missing DATABASE_URL only causes an
        error when the first DB-bound request arrives.
        """
        if not v:
            environment = info.data.get("ENVIRONMENT", "development")
            if environment == "production":
                # Log a clear warning but do NOT crash at import time.
                # The startup_event and migration script will surface the
                # error with a useful message.
                import logging as _logging
                _logging.getLogger(__name__).critical(
                    "DATABASE_URL secret is not set in Fly.io. "
                    "Run: flyctl secrets set DATABASE_URL=<your-supabase-url>"
                )
                return ""
            # Dev default only if not in production
            return "postgresql+asyncpg://fiscwise:dev_password@localhost:5432/fiscwise_db"

        if isinstance(v, str):
            # Parse URL and convert to asyncpg dialect
            parsed = urlparse(v)

            # Ensure asyncpg scheme
            if parsed.scheme == "postgres":
                parsed = parsed._replace(scheme="postgresql+asyncpg")
            elif parsed.scheme == "postgresql" and "+asyncpg" not in parsed.scheme:
                parsed = parsed._replace(scheme="postgresql+asyncpg")

            # Parse and fix query parameters
            params = parse_qs(parsed.query, keep_blank_values=True)

            # Remove sslmode (asyncpg doesn't support it)
            if "sslmode" in params:
                del params["sslmode"]

            # Add asyncpg-compatible SSL params
            if "ssl" not in params:
                params["ssl"] = ["require"]
            if "statement_cache_size" not in params:
                params["statement_cache_size"] = ["0"]

            # Rebuild query string
            new_query = urlencode(params, doseq=True)

            # Rebuild URL
            return urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                new_query,
                parsed.fragment
            ))
        return v

    # Redis — optional; not used in the current MVP feature set.
    # When rate-limiting or caching is added, set this secret in Fly.io.
    REDIS_URL: str = ""
    
    # JWT Authentication
    JWT_SECRET_KEY: str = ""
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    @field_validator("JWT_SECRET_KEY", mode="before")
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """Ensure JWT_SECRET_KEY is set securely.

        Same reasoning as DATABASE_URL: do not crash at import time so
        that the health endpoint can respond.  A missing key is surfaced
        as a 500 on the first auth request rather than killing the process.
        """
        environment = info.data.get("ENVIRONMENT", "development")

        if not v:
            if environment == "production":
                import logging as _logging
                _logging.getLogger(__name__).critical(
                    "JWT_SECRET_KEY secret is not set in Fly.io. "
                    "Run: flyctl secrets set JWT_SECRET_KEY=$(openssl rand -hex 64)"
                )
                return ""
            # Dev default only if not in production
            return "dev_secret_key_do_not_use_in_production_change_in_railway"

        if environment == "production" and "dev_secret" in v.lower():
            # NEVER raise ValueError here — it causes a ValidationError at import
            # time (settings = Settings()) which kills the process before uvicorn
            # starts, resulting in 0.0.0.0:8000 never being bound.
            # Surface as CRITICAL log instead; the health endpoint still responds
            # and the operator can fix the secret without a redeploy.
            import logging as _logging
            _logging.getLogger(__name__).critical(
                "JWT_SECRET_KEY appears to use a development default in production. "
                "Auth endpoints will be insecure. "
                "Regenerate with: flyctl secrets set JWT_SECRET_KEY=$(openssl rand -hex 64)"
            )
        return v
    
    # CORS
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:8000"

    # Public URL (used for widget script generation)
    PUBLIC_URL: str = "https://api.fiscwise.com.br"
    
    # Google OAuth
    GOOGLE_CLIENT_ID: str = ""

    # Supabase Storage
    SUPABASE_URL: str = ""
    SUPABASE_SECRET_KEY: str = ""

    # AI Services (optional — RAG engine removed in Phase 5)
    ANTHROPIC_API_KEY: str = ""
    VOYAGE_API_KEY: str = ""
    
    @field_validator("DEBUG", mode="before")
    @classmethod
    def validate_debug_mode(cls, v, info) -> bool:
        """Ensure DEBUG is False in production.

        Pydantic passes env var values as strings before coercion.
        Normalise to a real bool here so the comparison is reliable.

        NOTE: We do NOT raise ValueError here.  Raising at import time
        would crash the process before uvicorn ever starts, resulting in a
        502 Bad Gateway on Fly.io even though /api/v1/health does not need
        DEBUG to be set.  Instead we silently force DEBUG=False in
        production and emit a CRITICAL log so the issue is visible in logs.
        """
        import logging as _logging

        # Normalise string → bool  ("False" / "false" / "0" → False)
        if isinstance(v, str):
            v = v.lower() not in ("false", "0", "no", "off")

        environment = info.data.get("ENVIRONMENT", "development")
        if environment == "production" and v is True:
            _logging.getLogger(__name__).critical(
                "DEBUG=True detected in production environment. "
                "Forcing DEBUG=False. Set DEBUG=False (or omit the var) "
                "in Fly.io secrets to suppress this warning."
            )
            return False
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
