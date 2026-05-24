"""Unit tests for tenant isolation in authentication dependencies."""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.core.deps import _set_current_tenant_context, get_current_user
from app.core.security import create_access_token
from app.models.user import UserRole


class FakeScalarResult:
    def __init__(self, user):
        self.user = user

    def scalar_one_or_none(self):
        return self.user


class FakeUserSession:
    def __init__(self, user):
        self.user = user
        self.statements = []

    async def execute(self, statement, parameters=None):
        self.statements.append((statement, parameters))
        return FakeScalarResult(self.user)


class FakeSQLiteSession:
    def __init__(self):
        self.statements = []

    def get_bind(self):
        return SimpleNamespace(dialect=SimpleNamespace(name="sqlite"))

    async def execute(self, statement, parameters=None):
        self.statements.append((statement, parameters))


@pytest.mark.asyncio
async def test_current_user_rejects_tenant_header_mismatch():
    user_tenant_id = uuid.uuid4()
    request_tenant_id = uuid.uuid4()
    user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=user_tenant_id,
        email="owner@example.com",
        role=UserRole.OWNER,
        is_active=True,
    )
    request = SimpleNamespace(state=SimpleNamespace(tenant_id=str(request_tenant_id)))
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user_tenant_id),
        role=user.role.value,
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(request=request, token=token, db=FakeUserSession(user))

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Tenant header does not match authenticated user"


@pytest.mark.asyncio
async def test_current_user_sets_postgres_rls_tenant_context():
    tenant_id = uuid.uuid4()
    user = SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="owner@example.com",
        role=UserRole.OWNER,
        is_active=True,
    )
    request = SimpleNamespace(state=SimpleNamespace(tenant_id=str(tenant_id)))
    token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(tenant_id),
        role=user.role.value,
    )
    db = FakeUserSession(user)

    result = await get_current_user(request=request, token=token, db=db)

    assert result is user
    assert len(db.statements) == 2
    set_context_statement, parameters = db.statements[0]
    assert "set_config('app.current_tenant_id'" in str(set_context_statement)
    assert parameters == {"tenant_id": str(tenant_id)}


@pytest.mark.asyncio
async def test_rls_tenant_context_is_skipped_for_non_postgresql_sessions():
    db = FakeSQLiteSession()

    await _set_current_tenant_context(db, uuid.uuid4())

    assert db.statements == []
