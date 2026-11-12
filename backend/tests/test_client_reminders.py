"""POST /clients/{id}/reminders envia e-mail real ao cliente (B-02).

Antes o botão "Enviar por E-mail" do cockpit era um setTimeout com toast
"enviado" — não existia endpoint nenhum.
"""

from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import select

from app.models.notification import NotificationMessage
from app.models.obligation import DocumentChecklistItem
from app.models.operations import AccountReceivable
from app.services import email_service


def _capture(monkeypatch, ok=True):
    calls = []

    async def fake_send(to, subject, html, idempotency_key=None):
        calls.append((to, subject, html))
        return ok

    monkeypatch.setattr(email_service, "send_email", fake_send)
    return calls


async def test_custom_envia_mensagem_do_usuario(client_with_auth_a, monkeypatch):
    http, _, client, db = client_with_auth_a
    calls = _capture(monkeypatch)
    r = http.post(f"/api/v1/clients/{client.id}/reminders", json={"kind": "custom", "message": "Olá, <b>teste</b>"})
    assert r.status_code == 200, r.text
    assert r.json()["sent"] is True
    assert calls[0][0] == client.email
    assert "&lt;b&gt;teste&lt;/b&gt;" in calls[0][2]  # texto do usuário é escapado
    msg = (await db.execute(select(NotificationMessage))).scalar_one()
    assert msg.status == "sent" and msg.channel == "email" and msg.client_id == client.id


async def test_pending_documents_lista_pendencias(client_with_auth_a, monkeypatch):
    http, _, client, db = client_with_auth_a
    db.add(DocumentChecklistItem(
        tenant_id=client.tenant_id, client_id=client.id,
        competence_month=date.today().replace(day=1), document_name="Folha de pagamento", status="pending",
    ))
    await db.commit()
    calls = _capture(monkeypatch)
    r = http.post(f"/api/v1/clients/{client.id}/reminders", json={"kind": "pending_documents"})
    assert r.status_code == 200, r.text
    assert "Folha de pagamento" in calls[0][2]


async def test_payment_lista_cobrancas_abertas(client_with_auth_a, monkeypatch):
    http, _, client, db = client_with_auth_a
    db.add(AccountReceivable(
        tenant_id=client.tenant_id, client_id=client.id, description="Honorários - 2026-11",
        amount=Decimal("1234.50"), due_date=date.today() + timedelta(days=2), status="pending",
    ))
    await db.commit()
    calls = _capture(monkeypatch)
    r = http.post(f"/api/v1/clients/{client.id}/reminders", json={"kind": "payment"})
    assert r.status_code == 200, r.text
    assert "1234,50" in calls[0][2] and "Honorários - 2026-11" in calls[0][2]


async def test_email_desligado_nao_finge_sucesso(client_with_auth_a, monkeypatch):
    http, _, client, _ = client_with_auth_a
    _capture(monkeypatch, ok=False)
    monkeypatch.setattr(email_service, "is_configured", lambda: False)
    r = http.post(f"/api/v1/clients/{client.id}/reminders", json={"kind": "payment"})
    data = r.json()
    assert data["sent"] is False and data["reason"] == "email_disabled"


async def test_custom_sem_mensagem_422_e_outro_tenant_404(client_with_auth_a, client_b):
    http, _, client, _ = client_with_auth_a
    assert http.post(f"/api/v1/clients/{client.id}/reminders", json={"kind": "custom"}).status_code == 422
    assert http.post(f"/api/v1/clients/{client_b.id}/reminders", json={"kind": "payment"}).status_code == 404
