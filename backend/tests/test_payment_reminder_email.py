"""Lembrete de cobrança agendado envia e-mail real ao cliente (B-02).

Antes só gravava audit_event; nada chegava ao cliente.
"""

from datetime import datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.models.notification import NotificationMessage
from app.models.operations import AccountReceivable
from app.services import email_service
from app.services.scheduler import TZ_BR, send_payment_reminders_scheduled


async def _seed(test_db, tenant_a, client_a, days_ahead=3):
    due = datetime.now(TZ_BR).date() + timedelta(days=days_ahead)
    test_db.add(AccountReceivable(
        tenant_id=tenant_a.id, client_id=client_a.id,
        description="Honorários - 2026-11", amount=Decimal("350.00"),
        due_date=due, status="pending",
    ))
    await test_db.commit()


@pytest.mark.parametrize("ok,expected", [(True, "sent"), (False, "failed")])
async def test_lembrete_envia_e_registra_status_real(test_db, tenant_a, client_a, monkeypatch, ok, expected):
    await _seed(test_db, tenant_a, client_a)
    calls = []

    async def fake_send(to, subject, html, idempotency_key=None):
        calls.append((to, subject, html))
        return ok

    monkeypatch.setattr(email_service, "send_email", fake_send)
    monkeypatch.setattr(email_service, "is_configured", lambda: True)

    await send_payment_reminders_scheduled()

    assert len(calls) == 1 and calls[0][0] == client_a.email
    assert "350,00" in calls[0][2] and "vence em 3 dia" in calls[0][2]
    msgs = (await test_db.execute(select(NotificationMessage))).scalars().all()
    assert len(msgs) == 1
    assert msgs[0].status == expected and msgs[0].channel == "email"


async def test_lembrete_nao_duplica_no_mesmo_dia(test_db, tenant_a, client_a, monkeypatch):
    await _seed(test_db, tenant_a, client_a, days_ahead=0)
    calls = []

    async def fake_send(to, subject, html, idempotency_key=None):
        calls.append(to)
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)
    await send_payment_reminders_scheduled()
    await send_payment_reminders_scheduled()

    assert len(calls) == 1
    msgs = (await test_db.execute(select(NotificationMessage))).scalars().all()
    assert len(msgs) == 1 and msgs[0].status == "sent"


async def test_fora_das_datas_alvo_nao_envia(test_db, tenant_a, client_a, monkeypatch):
    await _seed(test_db, tenant_a, client_a, days_ahead=5)
    calls = []

    async def fake_send(*a, **k):
        calls.append(1)
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)
    await send_payment_reminders_scheduled()
    assert calls == []
