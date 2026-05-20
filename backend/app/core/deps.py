"""
Dependency Injection for ContaFlow

FastAPI dependencies for database sessions, authentication, and authorization.
"""

import logging
import uuid
from typing import AsyncGenerator, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.user import User

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ---------------------------------------------------------------------------
# Lazy engine initialisation — engine is created on first use, not at import
# time. This prevents the application from crashing during startup if
# DATABASE_URL is not yet available in the environment (e.g. during the
# Fly.io healthcheck grace period before secrets are injected).
# ---------------------------------------------------------------------------

_engine = None
_AsyncSessionLocal: Optional[async_sessionmaker] = None


def _sanitize_database_url(url: str) -> str:
    """Convert DATABASE_URL to asyncpg-compatible format.

    Handles Supabase URLs that include sslmode parameter, which asyncpg doesn't support.
    Converts postgres:// to postgresql+asyncpg:// and replaces sslmode with ssl param.
    """
    # Parse the URL
    parsed = urlparse(url)

    # Ensure asyncpg scheme
    if parsed.scheme == "postgres":
        parsed = parsed._replace(scheme="postgresql+asyncpg")

    # Parse and fix query parameters
    params = parse_qs(parsed.query, keep_blank_values=True)

    # Remove sslmode (asyncpg doesn't support it)
    if "sslmode" in params:
        del params["sslmode"]

    # Add asyncpg-compatible SSL params
    params["ssl"] = ["require"]
    params["statement_cache_size"] = ["0"]

    # Rebuild query string
    new_query = urlencode(params, doseq=True)

    # Rebuild URL
    fixed_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    return fixed_url


def _get_engine():
    """Return (and lazily create) the shared async engine.

    Raises RuntimeError with a clear message when DATABASE_URL is not
    configured so that the error surfaces in Fly.io logs instead of a
    cryptic sqlalchemy exception.
    """
    global _engine, _AsyncSessionLocal
    if _engine is None:
        if not settings.DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL is not configured. "
                "Set the secret in Fly.io with: "
                "flyctl secrets set DATABASE_URL=<your-supabase-connection-string>"
            )

        # Fix DATABASE_URL for asyncpg compatibility
        db_url = _sanitize_database_url(settings.DATABASE_URL)

        if db_url != settings.DATABASE_URL:
            logger.info("Converted DATABASE_URL from postgres to postgresql+asyncpg with SSL params")

        logger.info("Creating database engine for %s...", db_url[:40])
        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
        )
        _AsyncSessionLocal = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _engine, _AsyncSessionLocal


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for getting async database session.

    Yields an async SQLAlchemy session and ensures it's closed after use.
    The engine is initialised lazily on first call so that import-time errors
    are avoided when DATABASE_URL is not yet present in the environment.

    Yields:
        AsyncSession: SQLAlchemy async session
    """
    _, session_factory = _get_engine()
    async with session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency for getting the current authenticated user.
    
    Decodes the JWT token, validates it, and retrieves the user from database.
    Raises HTTPException if token is invalid or user not found/inactive.
    
    Args:
        token: JWT access token from Authorization header
        db: Database session dependency
        
    Returns:
        User: The authenticated user object
        
    Raises:
        HTTPException: 401 if token is invalid, expired, or user not found/inactive
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Decode JWT token
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        # Extract user_id from token payload
        user_id_str: str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
            
        # Convert string to UUID
        try:
            user_id = uuid.UUID(user_id_str)
        except ValueError:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Query user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    # Validate user exists and is active
    if user is None:
        raise credentials_exception
    
    # Ensure token tenant_id matches user tenant ownership
    token_tenant_id = payload.get("tenant_id")
    if token_tenant_id is None or token_tenant_id != str(user.tenant_id):
        raise credentials_exception

    request_tenant_id = getattr(request.state, "tenant_id", None)
    if request_tenant_id is not None and request_tenant_id != str(user.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant header does not match authenticated user"
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    return user
