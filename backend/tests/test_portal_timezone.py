"""Convites do portal com fuso: utcnow() naive x coluna aware dava 500 no Postgres."""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.api.v1.endpoints.portal import _as_utc, _is_expired
from app.core.config import Settings
from app.models.operations import ClientPortalInvite


def test_as_utc_normaliza_naive_e_aware():
    naive = datetime(2026, 1, 1, 12, 0)
    aware = datetime(2026, 1, 1, 9, 0, tzinfo=timezone(timedelta(hours=-3)))
    assert _as_utc(naive) == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert _as_utc(aware) == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    assert _as_utc(None) is None
    # Ambos comparáveis com agora (aware) sem TypeError.
    assert _is_expired(naive) and _is_expired(aware)
    assert not _is_expired(None)


def test_portal_url_padrao_deriva_de_app_url():
    assert Settings(APP_URL="https://app.x.com/", PORTAL_URL="").portal_url == "https://app.x.com/portal"
    assert Settings(PORTAL_URL="https://p.x.com/portal/").portal_url == "https://p.x.com/portal"


async def test_convite_criado_lido_e_aceito(client_with_auth_a):
    http, _, client_a, _ = client_with_auth_a
    resp = http.post(
        "/api/v1/portal/invites",
        json={"client_id": str(client_a.id), "email": "tz@cliente-a.com"},
    )
    assert resp.status_code == 201, resp.text
    invite_id = resp.json()["invite_id"]
    http.headers.pop("Authorization")
    assert http.get(f"/api/v1/portal/invites/{invite_id}").status_code == 200
    resp = http.post(
        f"/api/v1/portal/invites/{invite_id}/accept",
        json={"invite_id": invite_id, "password": "senha-forte-123", "full_name": "Cliente"},  # gitleaks:allow
    )
    assert resp.status_code == 200, resp.text


async def test_convite_expirado_devolve_410(client_with_auth_a):
    http, _, client_a, test_db = client_with_auth_a
    resp = http.post(
        "/api/v1/portal/invites",
        json={"client_id": str(client_a.id), "email": "exp@cliente-a.com"},
    )
    invite_id = uuid.UUID(resp.json()["invite_id"])
    invite = (
        await test_db.execute(select(ClientPortalInvite).where(ClientPortalInvite.id == invite_id))
    ).scalar_one()
    # Valor com fuso (como o Postgres devolve) — antes comparava com utcnow() naive.
    invite.expires_at = datetime.now(timezone.utc) - timedelta(days=1)
    await test_db.commit()
    assert http.get(f"/api/v1/portal/invites/{invite_id}").status_code == 410
