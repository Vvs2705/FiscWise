"""
Dependency Injection for FiscWise

FastAPI dependencies for database sessions, authentication, and authorization.
"""

import logging
import re
import uuid
from datetime import timezone
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.user import User, UserRole


_CLIENT_PORTAL_PATHS = frozenset({"/api/v1/portal/my-data", "/api/v1/portal/my-overview"})


def _client_path_allowed(path: str) -> bool:
    return path.startswith("/api/v1/auth/") or path.rstrip("/") in _CLIENT_PORTAL_PATHS

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
    """Convert DATABASE_URL to asyncpg-compatible format using regex.

    Uses regex instead of urlparse/urlunparse to avoid corruption of
    URL-encoded characters in passwords (e.g. %23 for #, %40 for @).
    statement_cache_size is NOT added here — passed as integer via
    connect_args to avoid asyncpg TypeError (string vs int comparison).
    """
    url = re.sub(r'^postgres(?:ql)?(?:\+\w+)?://', 'postgresql+asyncpg://', url)

    if '?' in url:
        base, qs = url.split('?', 1)
        params = []
        for part in qs.split('&'):
            if part.startswith('sslmode=') or part.startswith('ssl=') or part in ('sslmode', 'ssl'):
                continue
            if part:
                params.append(part)
    else:
        base = url
        params = []

    params.append('ssl=require')
    return f"{base}?{'&'.join(params)}"


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

        logger.info("Creating database engine")
        _engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
            pool_pre_ping=True,
            pool_size=5,
            max_overflow=10,
            connect_args={"statement_cache_size": 0},
        )
        _AsyncSessionLocal = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False,
        )
    return _engine, _AsyncSessionLocal


def get_sessionmaker() -> async_sessionmaker:
    """Return the shared async sessionmaker."""
    _, session_factory = _get_engine()
    return session_factory


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


async def _set_current_tenant_context(db: AsyncSession, tenant_id: uuid.UUID) -> None:
    """Set the current tenant in the PostgreSQL transaction for RLS policies."""
    get_bind = getattr(db, "get_bind", None)
    if callable(get_bind):
        bind = get_bind()
        dialect_name = getattr(getattr(bind, "dialect", None), "name", None)
        if dialect_name and dialect_name != "postgresql":
            return

    # Guarda na sessão para reaplicar a cada transação nova: set_config(..., true)
    # vale só até o commit, e depois dele as policies com "OR tenant IS NULL"
    # liberavam tudo no resto da requisição (TEN-4).
    db.info["tenant_id"] = str(tenant_id)
    await db.execute(
        text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
        {"tenant_id": str(tenant_id)},
    )


@event.listens_for(Session, "after_begin")
def _reapply_tenant_context(session, transaction, connection) -> None:
    tenant_id = session.info.get("tenant_id")
    if tenant_id and connection.dialect.name == "postgresql":
        connection.execute(
            text("SELECT set_config('app.current_tenant_id', :tenant_id, true)"),
            {"tenant_id": tenant_id},
        )


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

        token_tenant_id_str = payload.get("tenant_id")
        if token_tenant_id_str is None:
            raise credentials_exception

        try:
            token_tenant_id = uuid.UUID(token_tenant_id_str)
        except ValueError:
            raise credentials_exception
        token_iat = payload.get("iat")
            
    except JWTError:
        raise credentials_exception

    await _set_current_tenant_context(db, token_tenant_id)
    
    # Query user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    # Validate user exists and is active
    if user is None:
        raise credentials_exception
    
    # Token emitido antes da última troca de senha não vale mais.
    valid_after = getattr(user, "tokens_valid_after", None)
    if valid_after is not None:
        if valid_after.tzinfo is None:  # SQLite devolve sem fuso
            valid_after = valid_after.replace(tzinfo=timezone.utc)
        if token_iat is None or token_iat < int(valid_after.timestamp()):
            raise credentials_exception

    # Ensure token tenant_id matches user tenant ownership
    if token_tenant_id != user.tenant_id:
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

    if user.role == UserRole.CLIENT and not _client_path_allowed(request.url.path):
        # Usuário CLIENT (portal) só alcança a própria conta e os próprios
        # dados do portal; todo o resto é rota de equipe do escritório.
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client portal users cannot access office routes"
        )

    return user
