"""
Comprehensive tests for registration and login endpoints.

Tests cover:
1. Registration: valid case, duplicate email, response schema
2. Login: valid credentials, invalid password, non-existent user, inactive user
3. Enum consistency: role and subscription status values
"""

import uuid
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_password_hash, verify_password
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole


# ============================================================================
# Registration Tests
# ============================================================================


class TestRegistration:
    """Tests for POST /api/v1/onboarding/register endpoint."""

    @pytest.mark.asyncio
    async def test_register_valid_request(self, client, test_db: AsyncSession):
        """
        When: Valid registration data is provided
        Then: Creates tenant with TRIAL status and owner user with OWNER role
        And: Returns access_token, tenant_id, user info
        """
        payload = {
            "company_name": "Contabilidade Silva & Associados",
            "document": "12.345.678/0001-90",
            "owner_email": "joao@silva.com",
            "owner_password": "SecurePass123!",
            "owner_full_name": "João Silva",
        }

        response = client.post("/api/v1/onboarding/register", json=payload)

        # Response status and schema
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "token_type" in data
        assert "tenant_id" in data
        assert "user" in data

        # User info in response
        user_info = data["user"]
        assert user_info["email"] == "joao@silva.com"
        assert user_info["full_name"] == "João Silva"
        assert user_info["role"] == "owner"

        # Verify database state
        tenant = await test_db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(data["tenant_id"]))
        )
        tenant_obj = tenant.scalar_one()
        assert tenant_obj.name == "Contabilidade Silva & Associados"
        assert tenant_obj.document == "12.345.678/0001-90"
        assert tenant_obj.subscription_status == SubscriptionStatus.TRIAL

        # Verify user was created with OWNER role
        user = await test_db.execute(
            select(User).where(User.email == "joao@silva.com")
        )
        user_obj = user.scalar_one()
        assert user_obj.role == UserRole.OWNER
        assert user_obj.is_active is True
        assert user_obj.tenant_id == tenant_obj.id

    @pytest.mark.asyncio
    async def test_register_duplicate_email_rejected(self, client, test_db: AsyncSession):
        """
        When: Registering with an email that already exists
        Then: Returns 400 with EMAIL_ALREADY_EXISTS error code
        """
        # First registration
        payload1 = {
            "company_name": "First Company",
            "owner_email": "duplicate@test.com",
            "owner_password": "SecurePass123!",
            "owner_full_name": "First User",
        }
        response1 = client.post("/api/v1/onboarding/register", json=payload1)
        assert response1.status_code == 200

        # Second registration with same email
        payload2 = {
            "company_name": "Second Company",
            "owner_email": "duplicate@test.com",
            "owner_password": "DifferentPass456!",
            "owner_full_name": "Second User",
        }
        response2 = client.post("/api/v1/onboarding/register", json=payload2)

        assert response2.status_code == 400
        assert response2.json()["detail"] == "Email 'duplicate@test.com' is already registered"
        assert response2.headers.get("X-Error-Code") == "EMAIL_ALREADY_EXISTS"

    @pytest.mark.asyncio
    async def test_register_password_hashing(self, client, test_db: AsyncSession):
        """
        When: Registering a new user
        Then: Password is hashed with bcrypt (not stored as plaintext)
        """
        payload = {
            "company_name": "Test Company",
            "owner_email": "test@example.com",
            "owner_password": "MyPassword123!",
            "owner_full_name": "Test User",
        }

        response = client.post("/api/v1/onboarding/register", json=payload)
        assert response.status_code == 200

        user = await test_db.execute(
            select(User).where(User.email == "test@example.com")
        )
        user_obj = user.scalar_one()

        # Hashed password should not equal plaintext
        assert user_obj.hashed_password != "MyPassword123!"

        # But verify_password should return True
        assert verify_password("MyPassword123!", user_obj.hashed_password) is True
        assert verify_password("WrongPassword", user_obj.hashed_password) is False

    @pytest.mark.asyncio
    async def test_register_minimal_fields(self, client, test_db: AsyncSession):
        """
        When: Registering with only required fields (no document, no full_name)
        Then: Registration succeeds with optional fields as None
        """
        payload = {
            "company_name": "Minimal Company",
            "owner_email": "minimal@test.com",
            "owner_password": "SecurePass123!",
        }

        response = client.post("/api/v1/onboarding/register", json=payload)
        assert response.status_code == 200

        user = await test_db.execute(
            select(User).where(User.email == "minimal@test.com")
        )
        user_obj = user.scalar_one()
        assert user_obj.full_name is None

    @pytest.mark.asyncio
    async def test_register_invalid_email(self, client):
        """
        When: Registering with invalid email format
        Then: Returns 422 validation error
        """
        payload = {
            "company_name": "Test Company",
            "owner_email": "not-an-email",
            "owner_password": "SecurePass123!",
        }

        response = client.post("/api/v1/onboarding/register", json=payload)
        assert response.status_code == 422  # Pydantic validation error

    @pytest.mark.asyncio
    async def test_register_short_password(self, client):
        """
        When: Registering with password < 8 characters
        Then: Returns 422 validation error
        """
        payload = {
            "company_name": "Test Company",
            "owner_email": "test@example.com",
            "owner_password": "Short1!",  # 7 chars
        }

        response = client.post("/api/v1/onboarding/register", json=payload)
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_register_empty_company_name(self, client):
        """
        When: Registering with empty company name
        Then: Returns 422 validation error
        """
        payload = {
            "company_name": "",
            "owner_email": "test@example.com",
            "owner_password": "SecurePass123!",
        }

        response = client.post("/api/v1/onboarding/register", json=payload)
        assert response.status_code == 422


# ============================================================================
# Login Tests
# ============================================================================


class TestLogin:
    """Tests for POST /api/v1/auth/login endpoint."""

    @pytest.mark.asyncio
    async def test_login_valid_credentials(self, client, test_db: AsyncSession, tenant_a: Tenant):
        """
        When: Login with correct email and password
        Then: Returns access_token, token_type, tenant_id, and user info
        """
        # Create user
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="login@test.com",
            hashed_password=get_password_hash("CorrectPassword123!"),
            full_name="Login Test User",
            role=UserRole.MEMBER,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        # Login
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "login@test.com", "password": "CorrectPassword123!"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert "tenant_id" in data
        assert data["user"]["email"] == "login@test.com"
        assert data["user"]["role"] == "member"

    @pytest.mark.asyncio
    async def test_login_invalid_password(self, client, test_db: AsyncSession, tenant_a: Tenant):
        """
        When: Login with correct email but wrong password
        Then: Returns 401 Unauthorized
        """
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="wrong.pass@test.com",
            hashed_password=get_password_hash("CorrectPassword123!"),
            role=UserRole.OWNER,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "wrong.pass@test.com", "password": "WrongPassword123!"}
        )

        assert response.status_code == 401
        assert "E-mail ou senha incorretos" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """
        When: Login with email that doesn't exist
        Then: Returns 401 Unauthorized (does not reveal user doesn't exist)
        """
        response = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@test.com", "password": "Password123!"}
        )

        assert response.status_code == 401
        assert "E-mail ou senha incorretos" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_inactive_user(self, client, test_db: AsyncSession, tenant_a: Tenant):
        """
        When: Login with an inactive user account
        Then: Returns 403 Forbidden with "Inactive user account" message
        """
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="inactive@test.com",
            hashed_password=get_password_hash("CorrectPassword123!"),
            role=UserRole.MEMBER,
            is_active=False,  # Inactive
        )
        test_db.add(user)
        await test_db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "inactive@test.com", "password": "CorrectPassword123!"}
        )

        assert response.status_code == 403
        assert "Conta inativa. Entre em contato com o suporte." in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_login_returns_correct_tenant_id(self, client, test_db: AsyncSession, tenant_a: Tenant):
        """
        When: Login as user from specific tenant
        Then: Returned tenant_id matches user's tenant_id
        """
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="tenant.user@test.com",
            hashed_password=get_password_hash("Password123!"),
            role=UserRole.ADMIN,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "tenant.user@test.com", "password": "Password123!"}
        )

        data = response.json()
        assert str(tenant_a.id) == data["tenant_id"]

    @pytest.mark.asyncio
    async def test_login_token_contains_user_claims(self, client, test_db: AsyncSession, tenant_a: Tenant):
        """
        When: Login successfully
        Then: JWT token contains user_id, tenant_id, and role claims
        """
        from jose import jwt
        from app.core.config import settings

        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="claims@test.com",
            hashed_password=get_password_hash("Password123!"),
            role=UserRole.OWNER,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "claims@test.com", "password": "Password123!"}
        )

        token = response.json()["access_token"]

        # Decode JWT (no verification for this test)
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert payload["sub"] == str(user.id)
        assert payload["tenant_id"] == str(tenant_a.id)
        assert payload["role"] == "owner"


# ============================================================================
# Enum Consistency Tests
# ============================================================================


class TestEnumConsistency:
    """Tests to verify enum values match database constraints."""

    @pytest.mark.asyncio
    async def test_user_role_enum_values(self):
        """
        Verify UserRole enum has expected values matching database.
        """
        expected_roles = {"owner", "admin", "member", "client"}
        actual_roles = {role.value for role in UserRole}
        assert actual_roles == expected_roles

    @pytest.mark.asyncio
    async def test_subscription_status_enum_values(self):
        """
        Verify SubscriptionStatus enum has expected values matching database.
        """
        expected_statuses = {"trial", "active", "suspended", "cancelled", "expired"}
        actual_statuses = {status.value for status in SubscriptionStatus}
        assert actual_statuses == expected_statuses

    @pytest.mark.asyncio
    async def test_user_role_serialization_in_response(self, client, test_db: AsyncSession, tenant_a: Tenant):
        """
        When: User with OWNER role logs in
        Then: Role is serialized as string "owner" in response (not enum object)
        """
        user = User(
            id=uuid.uuid4(),
            tenant_id=tenant_a.id,
            email="role.test@test.com",
            hashed_password=get_password_hash("Password123!"),
            role=UserRole.OWNER,
            is_active=True,
        )
        test_db.add(user)
        await test_db.commit()

        response = client.post(
            "/api/v1/auth/login",
            data={"username": "role.test@test.com", "password": "Password123!"}
        )

        data = response.json()
        # Role should be string, not object
        assert isinstance(data["user"]["role"], str)
        assert data["user"]["role"] == "owner"

    @pytest.mark.asyncio
    async def test_subscription_status_in_registration(self, client, test_db: AsyncSession):
        """
        When: New tenant is created via registration
        Then: subscription_status is set to "trial" (not "TRIAL")
        """
        payload = {
            "company_name": "Subscription Test",
            "owner_email": "sub.test@test.com",
            "owner_password": "Password123!",
        }

        response = client.post("/api/v1/onboarding/register", json=payload)
        tenant_id = response.json()["tenant_id"]

        tenant = await test_db.execute(
            select(Tenant).where(Tenant.id == uuid.UUID(tenant_id))
        )
        tenant_obj = tenant.scalar_one()

        # Status should be enum with lowercase value
        assert tenant_obj.subscription_status == SubscriptionStatus.TRIAL
        assert tenant_obj.subscription_status.value == "trial"
