"""Without OPENAI_API_KEY the AI endpoints answer 503 and do NOT consume chat quota."""

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import func, select

from app.core.config import settings
from app.core.plan_access import AI_NOT_CONFIGURED_DETAIL, PLAN_INTERMEDIARIO
from app.models.calculator import FiscalAssistantMessage


async def _count_msgs(db, tenant_id) -> int:
    res = await db.execute(
        select(func.count()).select_from(FiscalAssistantMessage).where(
            FiscalAssistantMessage.tenant_id == tenant_id
        )
    )
    return int(res.scalar_one() or 0)


@pytest.fixture
def no_ai_key(monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "")


@pytest.mark.asyncio
async def test_chat_without_key_returns_503_and_keeps_quota(client_with_auth_a, test_db, no_ai_key):
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()

    with patch(
        "app.api.v1.endpoints.calculator.chat_with_fiscal_assistant", new_callable=AsyncMock
    ) as mock_chat:
        resp = client.post("/api/v1/calculator/chat", json={"content": "Qual regime escolher?"})
        mock_chat.assert_not_called()

    assert resp.status_code == 503
    assert resp.json()["detail"] == AI_NOT_CONFIGURED_DETAIL
    assert await _count_msgs(test_db, user_a.tenant_id) == 0


@pytest.mark.asyncio
async def test_client_ai_summary_without_key_returns_503_and_keeps_quota(
    client_with_auth_a, test_db, no_ai_key
):
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()

    with patch(
        "app.api.v1.endpoints.operations.generate_client_operational_summary", new_callable=AsyncMock
    ) as mock_summary:
        resp = client.post(f"/api/v1/clients/{uuid.uuid4()}/ai-summary")
        mock_summary.assert_not_called()

    assert resp.status_code == 503
    assert resp.json()["detail"] == AI_NOT_CONFIGURED_DETAIL
    assert await _count_msgs(test_db, user_a.tenant_id) == 0


@pytest.mark.asyncio
async def test_chat_with_key_still_consumes_quota(client_with_auth_a, test_db, monkeypatch):
    monkeypatch.setattr(settings, "OPENAI_API_KEY", "sk-test")
    client, user_a, _, _ = client_with_auth_a
    user_a.tenant.plan_slug = PLAN_INTERMEDIARIO
    await test_db.commit()

    with patch(
        "app.api.v1.endpoints.calculator.chat_with_fiscal_assistant", new_callable=AsyncMock
    ) as mock_chat:
        mock_chat.return_value = ("ok", 10)
        resp = client.post("/api/v1/calculator/chat", json={"content": "Oi"})

    assert resp.status_code == 201
    assert resp.json()["remaining_quota"] == 19
