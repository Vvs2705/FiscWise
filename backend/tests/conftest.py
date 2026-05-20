"""Shared test setup for ContaFlow backend tests."""

import os
import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash, create_access_token
from app.models.base import Base
from app.models.operations import AccountingClient
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole


os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-at-least-32-chars-long")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("VOYAGE_API_KEY", "test")


@pytest.fixture
def client() -> TestClient:
    """FastAPI test client with production middleware enabled."""
    from app.main import app

    return TestClient(app)


# ============================================================================
# Async Database Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_db():
    """In-memory SQLite database for async tests.

    SQLite does not enforce PostgreSQL ENUM types, so SQLAlchemy will create
    the columns as VARCHAR — acceptable for unit tests that only verify
    application-layer logic, not database constraints.
    """
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()

    await engine.dispose()


# ============================================================================
# Tenant and User Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def tenant_a(test_db: AsyncSession) -> Tenant:
    """Create tenant A for isolation tests."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Accounting Firm A",
        subscription_status=SubscriptionStatus.TRIAL,
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def tenant_b(test_db: AsyncSession) -> Tenant:
    """Create tenant B for isolation tests."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Accounting Firm B",
        subscription_status=SubscriptionStatus.TRIAL,
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)
    return tenant


@pytest_asyncio.fixture
async def user_a(test_db: AsyncSession, tenant_a: Tenant) -> User:
    """Create user belonging to tenant A."""
    user = User(
        id=uuid.uuid4(),
        email="user.a@firma-a.com",
        hashed_password=get_password_hash("password123"),
        full_name="User A",
        tenant_id=tenant_a.id,
        role=UserRole.OWNER,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


@pytest_asyncio.fixture
async def user_b(test_db: AsyncSession, tenant_b: Tenant) -> User:
    """Create user belonging to tenant B."""
    user = User(
        id=uuid.uuid4(),
        email="user.b@firma-b.com",
        hashed_password=get_password_hash("password123"),
        full_name="User B",
        tenant_id=tenant_b.id,
        role=UserRole.MEMBER,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)
    return user


# ============================================================================
# Resource Fixtures (Clients, etc.)
# ============================================================================


@pytest_asyncio.fixture
async def client_a(test_db: AsyncSession, tenant_a: Tenant) -> AccountingClient:
    """Create a client for tenant A."""
    ac = AccountingClient(
        id=uuid.uuid4(),
        tenant_id=tenant_a.id,
        name="Client from Firm A",
        document="11.222.333/0001-81",
        entity_type="pj",
        tax_regime="lucro_presumido",
        email="client.a@example.com",
        status="active",
    )
    test_db.add(ac)
    await test_db.commit()
    await test_db.refresh(ac)
    return ac


@pytest_asyncio.fixture
async def client_b(test_db: AsyncSession, tenant_b: Tenant) -> AccountingClient:
    """Create a client for tenant B."""
    ac = AccountingClient(
        id=uuid.uuid4(),
        tenant_id=tenant_b.id,
        name="Client from Firm B",
        document="44.555.666/0001-77",
        entity_type="pj",
        status="active",
    )
    test_db.add(ac)
    await test_db.commit()
    await test_db.refresh(ac)
    return ac


# ============================================================================
# HTTP Client with Auth (for integration tests)
# ============================================================================


@pytest_asyncio.fixture
async def client_with_auth_a(test_db: AsyncSession, user_a: User, client_a: AccountingClient):
    """HTTP client with auth token for user A."""
    from app.main import app
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: test_db

    http_client = TestClient(app)

    token = create_access_token(
        user_id=str(user_a.id),
        tenant_id=str(user_a.tenant_id),
        role=user_a.role.value,
    )

    http_client.headers.update({"Authorization": f"Bearer {token}"})

    yield http_client, user_a, client_a, test_db

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def client_with_auth_b(test_db: AsyncSession, user_b: User, client_b: AccountingClient):
    """HTTP client with auth token for user B."""
    from app.main import app
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: test_db

    http_client = TestClient(app)

    token = create_access_token(
        user_id=str(user_b.id),
        tenant_id=str(user_b.tenant_id),
        role=user_b.role.value,
    )

    http_client.headers.update({"Authorization": f"Bearer {token}"})

    yield http_client, user_b, client_b, test_db

    app.dependency_overrides.clear()
