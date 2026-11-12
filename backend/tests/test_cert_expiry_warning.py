"""POST /notifications/cert-expiry-warning envia e-mail de verdade (B-02).

Antes: criava NotificationMessage sem `body` (NOT NULL) → IntegrityError/500,
e o frontend dizia "enviado com sucesso" sem nada sair.
"""

from sqlalchemy import select

from app.models.notification import NotificationMessage
from app.services import email_service

URL = "/api/v1/notifications/cert-expiry-warning"


def _payload(client):
    return {
        "client_id": str(client.id),
        "client_name": client.name,
        "cert_label": "e-CNPJ A1",
        "days_until_expiry": 12,
    }


async def test_envia_ao_email_do_cliente(client_with_auth_a, monkeypatch):
    http, _, client, db = client_with_auth_a
    calls = []

    async def fake_send(to, subject, html, idempotency_key=None):
        calls.append((to, subject, html))
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)
    r = http.post(URL, json=_payload(client))

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["sent"] is True and data["status"] == "sent" and data["reason"] is None
    assert calls and calls[0][0] == client.email
    assert "e-CNPJ A1" in calls[0][2] and "12 dia" in calls[0][2]
    msg = (await db.execute(select(NotificationMessage))).scalar_one()
    assert msg.status == "sent" and msg.sent_at is not None
    assert msg.channel == "email" and msg.recipient == client.email and msg.body


async def test_email_desligado_responde_a_verdade(client_with_auth_a, monkeypatch):
    http, _, client, db = client_with_auth_a

    async def fake_send(*a, **k):
        return False

    monkeypatch.setattr(email_service, "send_email", fake_send)
    monkeypatch.setattr(email_service, "is_configured", lambda: False)
    r = http.post(URL, json=_payload(client))

    assert r.status_code == 200, r.text
    data = r.json()
    assert data["queued"] is False and data["sent"] is False
    assert data["reason"] == "email_disabled"
    assert "RESEND_ENABLED" in data["message"]
    msg = (await db.execute(select(NotificationMessage))).scalar_one()
    assert msg.status == "skipped" and msg.error_message == "email_disabled"


async def test_cliente_de_outro_escritorio_404(client_with_auth_a, client_b):
    http, _, _, _ = client_with_auth_a
    r = http.post(URL, json=_payload(client_b))
    assert r.status_code == 404
