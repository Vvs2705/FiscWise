"""
Dependency Injection for FiscWise

FastAPI dependencies for database sessions, authentication, and authorization.
"""

import logging
import re
import uuid
from datetime import datetime, timedelta, timezone
from typing import AsyncGenerator, Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.core.config import settings
from app.models.tenant import Tenant
from app.models.user import User, UserRole


_CLIENT_PORTAL_PATHS = frozenset({
    "/api/v1/portal/my-data",
    "/api/v1/portal/my-overview",
    "/api/v1/portal/my-documents",
})


def _client_path_allowed(path: str) -> bool:
    return path.startswith("/api/v1/auth/") or path.rstrip("/") in _CLIENT_PORTAL_PATHS


# Cadastro incompleto (escritório sem aceite dos Termos — p.ex. conta criada
# pelo antigo login Google automático) só alcança a própria conta e a tela de
# concluir cadastro. Todo o resto do sistema responde 403 SIGNUP_INCOMPLETE.
SIGNUP_INCOMPLETE_CODE = "SIGNUP_INCOMPLETE"
_SIGNUP_INCOMPLETE_PATHS = frozenset({
    "/api/v1/onboarding/complete-signup",
    "/api/v1/account/delete",
    "/api/v1/account/export",
})


def signup_complete(tenant: Optional[Tenant]) -> bool:
    """Escritório com cadastro concluído = aceitou os Termos de Uso."""
    return tenant is not None and getattr(tenant, "terms_accepted_at", None) is not None


def _signup_incomplete_path_allowed(path: str) -> bool:
    return path.startswith("/api/v1/auth/") or path.rstrip("/") in _SIGNUP_INCOMPLETE_PATHS


def ensure_signup_complete(tenant: Optional[Tenant], path: str) -> None:
    if signup_complete(tenant) or _signup_incomplete_path_allowed(path):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Conclua o cadastro do seu escritório para usar o FiscWise.",
        headers={"X-Error-Code": SIGNUP_INCOMPLETE_CODE},
    )

logger = logging.getLogger(__name__)

# OAuth2 scheme for token authentication
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")
# Mesma origem, mas sem 401 automático: usado por get_current_principal, que
# ainda pode autenticar pela chave de API.
oauth2_scheme_optional = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

API_KEY_HEADER = "X-API-Key"


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

    # Banco local (CI, docker-compose) não fala SSL; fora dele o SSL segue obrigatório.
    if not re.search(r'@(localhost|127\.0\.0\.1|postgres|db)(:\d+)?/', base):
        params.append('ssl=require')
    return f"{base}?{'&'.join(params)}" if params else base


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
    # Sem transação aberta, o hook after_begin abaixo aplica o contexto na
    # primeira consulta; executar aqui também dobrava o set_config.
    in_transaction = getattr(db, "in_transaction", None)
    if callable(in_transaction) and not in_transaction():
        return
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
        
        # Só access token entra nas rotas normais: token de propósito único
        # (reset de senha), de desafio 2FA (type=mfa) ou de dispositivo
        # (type=device, que só vale em /api/v1/sync/* via get_current_device)
        # é recusado aqui.
        if payload.get("purpose", "access") != "access" or payload.get("type") not in (None, "access"):
            raise credentials_exception

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
    
    # Usuário + tenant + assinatura numa ida só ao banco: o plan_access lê
    # current_user.tenant.subscription em quase toda rota.
    result = await db.execute(
        select(User)
        .options(joinedload(User.tenant).joinedload(Tenant.subscription))
        .where(User.id == user_id)
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

    if user.role != UserRole.CLIENT:
        ensure_signup_complete(user.tenant, request.url.path)

    return user


class DeviceAuthError(HTTPException):
    """401 do token de dispositivo com corpo {"detail": ..., "code": ...}.

    O cliente offline decide pelo `code` (device_revoked → apaga o banco local).
    Handler registrado em app/main.py.
    """

    def __init__(self, detail: str, code: str):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )
        self.code = code


def _device_auth_error(detail: str, code: str) -> DeviceAuthError:
    return DeviceAuthError(detail, code)


async def get_current_device(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """Autentica o token de dispositivo dos endpoints /api/v1/sync/*.

    Confere (docs/arquitetura/OFFLINE_SYNC.md 5.1): assinatura, type=device,
    dispositivo existe e pertence ao usuário/escritório do token, não revogado
    (401 code=device_revoked), usuário ativo, iat >= tokens_valid_after e
    X-Tenant-ID igual ao tenant do token. Token de usuário comum é recusado.
    Devolve (user, device) e atualiza last_seen_at.
    """
    from app.models.sync import SyncDevice

    invalid = _device_auth_error("Token de dispositivo inválido.", "device_token_invalid")
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        raise invalid
    if payload.get("type") != "device":
        raise invalid
    try:
        user_id = uuid.UUID(str(payload.get("sub")))
        tenant_id = uuid.UUID(str(payload.get("tenant_id")))
        device_id = uuid.UUID(str(payload.get("device_id")))
    except ValueError:
        raise invalid
    token_iat = payload.get("iat")

    request_tenant_id = getattr(request.state, "tenant_id", None)
    if request_tenant_id is not None and request_tenant_id != str(tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant header does not match authenticated user",
        )

    await _set_current_tenant_context(db, tenant_id)

    device = await db.scalar(select(SyncDevice).where(SyncDevice.id == device_id))
    if device is None or device.tenant_id != tenant_id or device.user_id != user_id:
        raise invalid
    if device.revoked_at is not None:
        raise _device_auth_error(
            "Este dispositivo foi desconectado do escritório. Entre novamente.", "device_revoked"
        )

    user = await db.scalar(select(User).where(User.id == user_id))
    if user is None or user.tenant_id != tenant_id or not user.is_active:
        raise invalid
    if user.role == UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Client portal users cannot access office routes",
        )
    valid_after = getattr(user, "tokens_valid_after", None)
    if valid_after is not None:
        if valid_after.tzinfo is None:  # SQLite devolve sem fuso
            valid_after = valid_after.replace(tzinfo=timezone.utc)
        if token_iat is None or token_iat < int(valid_after.timestamp()):
            raise _device_auth_error("Sessão expirada. Entre novamente.", "device_token_expired")

    # Teto de 180 dias da cadeia de renovações: depois disso só um login
    # online registra o dispositivo de novo (POST /sync/devices).
    from app.core.security import DEVICE_TOKEN_MAX_LIFETIME_DAYS, device_chain_started_at

    chain_started_at = device_chain_started_at(payload, fallback=device.created_at)
    if chain_started_at is not None and datetime.now(timezone.utc) - chain_started_at > timedelta(
        days=DEVICE_TOKEN_MAX_LIFETIME_DAYS
    ):
        raise _device_auth_error(
            "O acesso offline deste dispositivo venceu. Entre novamente com a internet ligada.",
            "device_token_expired",
        )
    request.state.device_chain_started_at = chain_started_at

    tenant = await db.scalar(select(Tenant).where(Tenant.id == tenant_id))
    ensure_signup_complete(tenant, request.url.path)

    device.last_seen_at = datetime.now(timezone.utc)
    await db.commit()
    return user, device


async def _authenticate_api_key(request: Request, raw_key: str, db: AsyncSession) -> User:
    """Autentica uma integração pela chave de API do tenant.

    A chave age em nome do OWNER ativo mais antigo do tenant (os endpoints
    usam current_user.tenant_id/role/id). O jeito de saber que veio de chave é
    request.state.auth_method == "api_key" (e request.state.api_key_id); o
    objeto User não é alterado.
    """
    from app.core.auth_rate_limiter import check_api_key_rate
    from app.services.api_key_service import verify_api_key

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid API key",
        headers={"WWW-Authenticate": "ApiKey"},
    )
    key = await verify_api_key(db, raw_key.strip())
    if key is None:
        raise invalid

    check_api_key_rate(str(key.id))

    request_tenant_id = getattr(request.state, "tenant_id", None)
    if request_tenant_id is not None and request_tenant_id != str(key.tenant_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant header does not match API key",
        )

    await _set_current_tenant_context(db, key.tenant_id)
    result = await db.execute(
        select(User)
        .where(
            User.tenant_id == key.tenant_id,
            User.role == UserRole.OWNER,
            User.is_active == True,  # noqa: E712
        )
        .order_by(User.created_at)
        .limit(1)
    )
    owner = result.scalar_one_or_none()
    if owner is None:
        raise invalid
    tenant = await db.scalar(select(Tenant).where(Tenant.id == key.tenant_id))
    ensure_signup_complete(tenant, request.url.path)

    request.state.auth_method = "api_key"
    request.state.api_key_id = str(key.id)
    return owner


async def get_current_principal(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme_optional),
    db: AsyncSession = Depends(get_db),
) -> User:
    """JWT (Authorization: Bearer) ou chave de API (X-API-Key).

    Só as rotas de operação liberadas para integração usam esta dependência;
    auth/*, account/*, billing/*, developer/*, admin/* e o resto continuam em
    get_current_user (JWT apenas). Com os dois cabeçalhos, vale o JWT.
    """
    if token:
        user = await get_current_user(request, token, db)
        request.state.auth_method = "jwt"
        return user

    raw_key = request.headers.get(API_KEY_HEADER)
    if raw_key:
        return await _authenticate_api_key(request, raw_key, db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated",
        headers={"WWW-Authenticate": "Bearer"},
    )
