"""O engine de documentos pendentes envia de verdade via email_service (B-02).

Antes: lia EMAIL_PROVIDER (inexistente) e importava o SDK `resend` (ausente) —
toda mensagem virava 'skipped' e nada chegava ao cliente.
"""

from datetime import date

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models.notification import NotificationMessage
from app.models.obligation import DocumentChecklistItem
from app.services import email_service
from app.services.notification_engine import notify_pending_documents_for_tenant


async def _seed_pending(test_db, tenant_a, client_a):
    comp = date.today().replace(day=1)
    test_db.add(DocumentChecklistItem(
        tenant_id=tenant_a.id, client_id=client_a.id,
        competence_month=comp, document_name="Extrato bancário", status="pending",
    ))
    await test_db.commit()
    return comp


@pytest.mark.parametrize("provider_ok,expected", [(True, "sent"), (False, "failed")])
async def test_status_reflete_envio_real(test_db, tenant_a, client_a, monkeypatch, provider_ok, expected):
    comp = await _seed_pending(test_db, tenant_a, client_a)
    calls = []

    async def fake_send(to, subject, html, idempotency_key=None):
        calls.append((to, subject, html))
        return provider_ok

    monkeypatch.setattr(email_service, "send_email", fake_send)
    # Envio "ligado" para que um False seja falha do provedor, não e-mail desligado.
    monkeypatch.setattr(email_service, "is_configured", lambda: True)

    counts = await notify_pending_documents_for_tenant(test_db, tenant_a.id, comp)

    assert len(calls) == 1 and calls[0][0] == client_a.email
    assert "Extrato bancário" in calls[0][2]
    assert f"{settings.portal_url}/login" in calls[0][2]
    msg = (await test_db.execute(select(NotificationMessage))).scalar_one()
    assert msg.status == expected
    assert msg.channel == "email" and msg.recipient == client_a.email
    assert (msg.sent_at is not None) == provider_ok
    assert counts[expected] == 1


async def test_email_desligado_fica_skipped_com_motivo(test_db, tenant_a, client_a, monkeypatch):
    comp = await _seed_pending(test_db, tenant_a, client_a)
    monkeypatch.setattr(email_service, "is_configured", lambda: False)

    async def fake_send(*a, **k):
        return False

    monkeypatch.setattr(email_service, "send_email", fake_send)
    await notify_pending_documents_for_tenant(test_db, tenant_a.id, comp)
    msg = (await test_db.execute(select(NotificationMessage))).scalar_one()
    assert msg.status == "skipped" and msg.error_message == "email_disabled"


def test_portal_url_deriva_de_app_url(monkeypatch):
    monkeypatch.setattr(settings, "PORTAL_URL", "")
    monkeypatch.setattr(settings, "APP_URL", "https://app.exemplo.com/")
    assert settings.portal_url == "https://app.exemplo.com/portal"
    monkeypatch.setattr(settings, "PORTAL_URL", "https://portal.exemplo.com/")
    assert settings.portal_url == "https://portal.exemplo.com"
