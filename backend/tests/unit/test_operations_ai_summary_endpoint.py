import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.api.v1.endpoints import operations
from app.core.plan_access import PLAN_FREE, PLAN_INTERMEDIARIO
from app.models.calculator import AssistantRole


class _ScalarsResult:
    def __init__(self, values):
        self._values = values

    def scalars(self):
        return self

    def all(self):
        return self._values


class _FakeDb:
    def __init__(self, execute_results=None):
        self._execute_results = list(execute_results or [])
        self.added = []
        self.flushed = False
        self.committed = False

    async def execute(self, _statement):
        return self._execute_results.pop(0)

    def add(self, item):
        self.added.append(item)

    async def flush(self):
        self.flushed = True

    async def commit(self):
        self.committed = True


def _user(plan_slug: str):
    tenant_id = uuid.uuid4()
    return SimpleNamespace(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email="owner@fiscwise.test",
        tenant=SimpleNamespace(plan_slug=plan_slug),
    )


@pytest.mark.asyncio
async def test_client_ai_summary_denies_free_plan() -> None:
    with pytest.raises(HTTPException) as exc_info:
        await operations.get_client_ai_summary(
            client_id=uuid.uuid4(),
            current_user=_user(PLAN_FREE),
            db=_FakeDb(),
        )

    assert exc_info.value.status_code == 403
    assert "requer o plano Intermediário" in exc_info.value.detail


@pytest.mark.asyncio
async def test_client_ai_summary_enforces_existing_chat_quota(monkeypatch) -> None:
    monkeypatch.setattr(
        operations,
        "check_chat_quota",
        AsyncMock(return_value=(False, 0)),
    )

    with pytest.raises(HTTPException) as exc_info:
        await operations.get_client_ai_summary(
            client_id=uuid.uuid4(),
            current_user=_user(PLAN_INTERMEDIARIO),
            db=_FakeDb(),
        )

    assert exc_info.value.status_code == 429
    assert "atingiu o limite de 20 mensagens mensais" in exc_info.value.detail


@pytest.mark.asyncio
async def test_client_ai_summary_generates_summary_and_consumes_quota(monkeypatch) -> None:
    client_id = uuid.uuid4()
    user = _user(PLAN_INTERMEDIARIO)
    db = _FakeDb(
        execute_results=[
            _ScalarsResult([]),
            _ScalarsResult([]),
            _ScalarsResult([]),
            _ScalarsResult([]),
        ]
    )
    client = SimpleNamespace(
        id=client_id,
        name="Clinica Exemplo",
        document="12.345.678/0001-90",
        status="active",
        tax_regime="simples_nacional",
        entity_type="pj",
        notes=None,
    )
    quota = AsyncMock(side_effect=[(True, 20), (True, 19)])
    summary = AsyncMock(return_value=("Cliente sem pendencias criticas.", 77))

    monkeypatch.setattr(operations, "check_chat_quota", quota)
    monkeypatch.setattr(operations, "_get_client_or_404", AsyncMock(return_value=client))
    monkeypatch.setattr(operations, "generate_client_operational_summary", summary)

    response = await operations.get_client_ai_summary(
        client_id=client_id,
        current_user=user,
        db=db,
    )

    assert response.summary == "Cliente sem pendencias criticas."
    assert response.remaining_quota == 19
    assert response.tokens_used == 77
    assert db.flushed is True
    assert db.committed is True
    assert [message.role for message in db.added] == [
        AssistantRole.USER,
        AssistantRole.ASSISTANT,
    ]
    summary.assert_called_once()
