"""
Integration tests for POST /api/v1/onboarding/register

These tests use an in-memory SQLite database via the test_db fixture and
override the FastAPI get_db dependency so no real Postgres/Fly.io connection
is needed.  They exercise the full request/response cycle including:

  - Happy path: tenant + user created, JWT returned
  - Duplicate email: 400 with EMAIL_ALREADY_EXISTS
  - Short password: 422 (Pydantic validation)
  - Missing required fields: 422

SQLite does not enforce PostgreSQL ENUM values, so these tests focus on
application logic, not database constraint validation.  The enum case bug
(UPPERCASE vs lowercase) is validated by a dedicated test that inserts with
the enum Python object directly and reads it back.
"""

import uuid

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole


# ---------------------------------------------------------------------------
# Fixture: override get_db with the in-memory test_db session
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def register_client(test_db: AsyncSession):
    """TestClient with get_db overridden to use the SQLite test_db session."""
    from app.main import app
    from app.core.deps import get_db

    app.dependency_overrides[get_db] = lambda: test_db
    yield TestClient(app, raise_server_exceptions=False)
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_tenant_success(register_client, test_db: AsyncSession):
    """New registration returns 200 with access_token and correct tenant_id."""
    payload = {
        "company_name": "Contabilidade Teste Ltda",
        "owner_email": "owner@teste.com",
        "owner_password": "SenhaSegura123!",
        "owner_full_name": "Dono Teste",
    }

    response = register_client.post("/api/v1/onboarding/register", json=payload)

    assert response.status_code == 200, response.text

    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert "tenant_id" in data
    assert data["user"]["email"] == "owner@teste.com"
    assert data["user"]["role"] == "owner"

    # Confirm tenant was actually persisted
    result = await test_db.execute(select(Tenant))
    tenants = result.scalars().all()
    assert len(tenants) == 1
    assert tenants[0].name == "Contabilidade Teste Ltda"
    assert tenants[0].subscription_status == SubscriptionStatus.TRIAL

    # Confirm user was persisted
    result = await test_db.execute(select(User))
    users = result.scalars().all()
    assert len(users) == 1
    assert users[0].email == "owner@teste.com"
    assert users[0].role == UserRole.OWNER
    assert users[0].is_active is True


@pytest.mark.asyncio
async def test_register_tenant_without_optional_fields(register_client, test_db: AsyncSession):
    """Registration with only required fields (no full_name, no document) succeeds."""
    payload = {
        "company_name": "Escritório Básico",
        "owner_email": "basico@escritorio.com",
        "owner_password": "Senha12345",
    }

    response = register_client.post("/api/v1/onboarding/register", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["user"]["full_name"] is None


# ---------------------------------------------------------------------------
# Duplicate email
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_duplicate_email_returns_400(register_client, test_db: AsyncSession):
    """Second registration with same email returns 400 EMAIL_ALREADY_EXISTS."""
    # Pre-populate a tenant and user
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Firma Existente",
        subscription_status=SubscriptionStatus.TRIAL,
    )
    test_db.add(tenant)
    await test_db.flush()

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="jaexiste@firma.com",
        hashed_password=get_password_hash("SenhaExistente1"),
        role=UserRole.OWNER,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()

    payload = {
        "company_name": "Nova Firma",
        "owner_email": "jaexiste@firma.com",
        "owner_password": "OutraSenha123",
    }

    response = register_client.post("/api/v1/onboarding/register", json=payload)

    assert response.status_code == 400
    assert response.headers.get("X-Error-Code") == "EMAIL_ALREADY_EXISTS"
    assert "already registered" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Pydantic validation errors (422)
# ---------------------------------------------------------------------------


def test_register_short_password_returns_422(register_client):
    """Passwords shorter than 8 characters fail Pydantic validation."""
    payload = {
        "company_name": "Empresa X",
        "owner_email": "user@empresa.com",
        "owner_password": "abc",  # too short
    }

    response = register_client.post("/api/v1/onboarding/register", json=payload)

    assert response.status_code == 422


def test_register_missing_company_name_returns_422(register_client):
    """Missing company_name field returns 422."""
    payload = {
        "owner_email": "user@empresa.com",
        "owner_password": "SenhaValida123",
    }

    response = register_client.post("/api/v1/onboarding/register", json=payload)

    assert response.status_code == 422


def test_register_invalid_email_returns_422(register_client):
    """Invalid email address returns 422."""
    payload = {
        "company_name": "Empresa Y",
        "owner_email": "not-an-email",
        "owner_password": "SenhaValida123",
    }

    response = register_client.post("/api/v1/onboarding/register", json=payload)

    assert response.status_code == 422


def test_register_company_name_too_short_returns_422(register_client):
    """company_name with 1 character (min=2) returns 422."""
    payload = {
        "company_name": "X",
        "owner_email": "user@empresa.com",
        "owner_password": "SenhaValida123",
    }

    response = register_client.post("/api/v1/onboarding/register", json=payload)

    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Enum case integrity (Python layer)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_subscription_status_stored_as_lowercase(register_client, test_db: AsyncSession):
    """SubscriptionStatus.TRIAL must produce the string 'trial', not 'TRIAL'.

    This is the exact mismatch that caused the 500 on Fly.io: the Python enum
    had lowercase values but the PostgreSQL enum was created with UPPERCASE.
    The fix_enum_case migration corrects the DB side; this test guards the
    Python side so the same regression cannot sneak back in.
    """
    assert SubscriptionStatus.TRIAL.value == "trial"
    assert SubscriptionStatus.ACTIVE.value == "active"
    assert SubscriptionStatus.SUSPENDED.value == "suspended"
    assert SubscriptionStatus.CANCELLED.value == "cancelled"
    assert SubscriptionStatus.EXPIRED.value == "expired"


@pytest.mark.asyncio
async def test_user_role_stored_as_lowercase(register_client, test_db: AsyncSession):
    """UserRole enum values must be lowercase — matches the fixed Postgres enum."""
    assert UserRole.OWNER.value == "owner"
    assert UserRole.ADMIN.value == "admin"
    assert UserRole.MEMBER.value == "member"


@pytest.mark.asyncio
async def test_tenant_subscription_status_roundtrip(test_db: AsyncSession):
    """Tenant created with TRIAL subscription_status reads back as TRIAL enum."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Roundtrip Test",
        subscription_status=SubscriptionStatus.TRIAL,
    )
    test_db.add(tenant)
    await test_db.commit()
    await test_db.refresh(tenant)

    assert tenant.subscription_status == SubscriptionStatus.TRIAL
    assert tenant.subscription_status.value == "trial"


@pytest.mark.asyncio
async def test_user_role_roundtrip(test_db: AsyncSession):
    """User created with OWNER role reads back as OWNER enum."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name="Role Roundtrip",
        subscription_status=SubscriptionStatus.TRIAL,
    )
    test_db.add(tenant)
    await test_db.flush()

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        email="owner@roundtrip.com",
        hashed_password=get_password_hash("Password123"),
        role=UserRole.OWNER,
        is_active=True,
    )
    test_db.add(user)
    await test_db.commit()
    await test_db.refresh(user)

    assert user.role == UserRole.OWNER
    assert user.role.value == "owner"
