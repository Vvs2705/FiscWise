"""Tests for plan access rules and admin plan operations."""

from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

from app.api.v1.endpoints import admin
from app.core import plan_access
from app.core.plan_access import (
    PLAN_FREE,
    PLAN_INTERMEDIARIO,
    PLAN_PREMIUM,
    check_chat_quota,
    has_plan,
    require_plan,
    resolve_plan,
)
from app.models.calculator import AssistantRole, FiscalAssistantMessage


def _request_from(ip: str = "127.0.0.1"):
    return SimpleNamespace(headers={}, client=SimpleNamespace(host=ip))


def _bearer(token: str) -> HTTPAuthorizationCredentials:
    return HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)


def test_unknown_or_missing_plan_is_treated_as_free_access():
    assert has_plan(None, PLAN_INTERMEDIARIO) is False
    assert has_plan("enterprise", PLAN_INTERMEDIARIO) is False

    with pytest.raises(HTTPException) as exc_info:
        require_plan("enterprise", PLAN_INTERMEDIARIO, "Chat fiscal")

    assert exc_info.value.status_code == 403
    assert "Intermedi" in exc_info.value.detail


def test_configured_superuser_email_resolves_to_premium(monkeypatch):
    monkeypatch.setattr(
        plan_access,
        "_SUPERUSER_EMAILS",
        frozenset({"owner@fiscwise.test"}),
    )

    assert resolve_plan(PLAN_FREE, "owner@fiscwise.test") == PLAN_PREMIUM
    assert resolve_plan(PLAN_INTERMEDIARIO, "normal@fiscwise.test") == PLAN_INTERMEDIARIO


@pytest.mark.asyncio
async def test_chat_quota_counts_only_current_month_user_messages(test_db, tenant_a):
    old_message = FiscalAssistantMessage(
        tenant_id=tenant_a.id,
        role=AssistantRole.USER,
        content="Mensagem de mes anterior",
        created_at=plan_access.datetime.now(plan_access.timezone.utc).replace(month=1, day=1),
    )
    assistant_message = FiscalAssistantMessage(
        tenant_id=tenant_a.id,
        role=AssistantRole.ASSISTANT,
        content="Resposta nao conta na franquia",
    )
    current_user_message = FiscalAssistantMessage(
        tenant_id=tenant_a.id,
        role=AssistantRole.USER,
        content="Mensagem atual",
    )
    test_db.add_all([old_message, assistant_message, current_user_message])
    await test_db.commit()

    has_quota, remaining = await check_chat_quota(
        tenant_a.id,
        PLAN_INTERMEDIARIO,
        test_db,
    )

    assert has_quota is True
    assert remaining == 19


@pytest.mark.asyncio
async def test_verify_admin_token_rejects_when_admin_operations_disabled(monkeypatch):
    monkeypatch.setattr(admin, "ADMIN_OPERATIONS_ALLOWED", False)
    monkeypatch.setattr(admin, "ADMIN_TOKEN", "secret-token")

    with pytest.raises(HTTPException) as exc_info:
        await admin.verify_admin_token(
            credentials=_bearer("secret-token"),
            request=_request_from(),
        )

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail == "Admin operations are disabled"


@pytest.mark.asyncio
async def test_verify_admin_token_rejects_invalid_token_with_401(monkeypatch):
    monkeypatch.setattr(admin, "ADMIN_OPERATIONS_ALLOWED", True)
    monkeypatch.setattr(admin, "ADMIN_TOKEN", "secret-token")

    with pytest.raises(HTTPException) as exc_info:
        await admin.verify_admin_token(
            credentials=_bearer("wrong-token"),
            request=_request_from(),
        )

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Invalid admin token"


@pytest.mark.asyncio
async def test_set_plan_by_email_updates_user_tenant_plan(test_db, user_a, tenant_a):
    tenant_a.plan_slug = PLAN_FREE
    await test_db.commit()

    response = await admin.set_plan_by_email(
        body=admin.SetPlanRequest(email=user_a.email, plan_slug=PLAN_PREMIUM),
        request=_request_from(),
        token="already-verified-token",
        db=test_db,
    )

    assert response["status"] == "updated"
    assert response["email"] == user_a.email
    assert response["old_plan"] == PLAN_FREE
    assert response["new_plan"] == PLAN_PREMIUM


@pytest.mark.asyncio
async def test_set_plan_by_email_rejects_invalid_plan_slug(test_db, user_a):
    with pytest.raises(HTTPException) as exc_info:
        await admin.set_plan_by_email(
            body=admin.SetPlanRequest(email=user_a.email, plan_slug="enterprise"),
            request=_request_from(),
            token="already-verified-token",
            db=test_db,
        )

    assert exc_info.value.status_code == 422
    assert "Invalid plan_slug" in exc_info.value.detail
