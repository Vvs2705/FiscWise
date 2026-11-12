"""Sync offline-first (docs/arquitetura/OFFLINE_SYNC.md, seção 10 — backend).

Cobre: registro/listagem/revogação/renovação de dispositivo, push idempotente,
LWW por campo com histórico, pull paginado com marca d'água, isolamento entre
escritórios, regra fiscal da nota, erro transitório (503 sem rejected),
`version` via REST e exclusão como status terminal.
"""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.core.security import create_access_token, create_device_token, get_password_hash
from app.domain.invoices.models import Invoice, InvoiceEvent, InvoiceIssuer
from app.models.audit import AuditEvent
from app.models.operations import AccountingClient
from app.models.sync import SyncConflict, SyncDevice, SyncEvent
from app.models.user import User, UserRole

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _register(http: TestClient, user_token_headers: dict | None = None, device_id=None, name="Chrome no Windows"):
    device_id = device_id or uuid.uuid4()
    resp = http.post(
        "/api/v1/sync/devices",
        json={"id": str(device_id), "name": name, "platform": "web", "app_version": "1.0.0"},
        headers=user_token_headers or {},
    )
    assert resp.status_code == 201, resp.text
    return device_id, resp.json()["device_token"]


def _dev_headers(token: str, tenant_id) -> dict:
    return {"Authorization": f"Bearer {token}", "X-Tenant-ID": str(tenant_id)}


def _event(device_id, entity_type, entity_id, operation, payload=None, base_version=None, event_id=None):
    return {
        "id": str(event_id or uuid.uuid4()),
        "device_id": str(device_id),
        "entity_type": entity_type,
        "entity_id": str(entity_id),
        "operation": operation,
        "payload": payload or {},
        "base_version": base_version,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def _push(http, headers, *events):
    return http.post("/api/v1/sync/push", json={"events": list(events)}, headers=headers)


@pytest.fixture
def ctx(client_with_auth_a):
    http, user, client_row, db = client_with_auth_a
    tenant_id, user_id, client_id = user.tenant_id, user.id, client_row.id
    device_id, token = _register(http)
    return {
        "http": http, "db": db, "tenant_id": tenant_id, "user_id": user_id,
        "client_id": client_id, "device_id": device_id, "headers": _dev_headers(token, tenant_id),
    }


async def _count(db, model, *where):
    return await db.scalar(select(func.count()).select_from(model).where(*where))


# ---------------------------------------------------------------------------
# dispositivos e autenticação
# ---------------------------------------------------------------------------


async def test_registro_listagem_e_reregistro_do_dispositivo(client_with_auth_a, test_db):
    http, user, _c, _db = client_with_auth_a
    tenant_id, owner_id = user.tenant_id, user.id
    device_id, token = _register(http)

    # mesmo id + mesmo usuário: atualiza (não duplica)
    resp = http.post("/api/v1/sync/devices", json={
        "id": str(device_id), "name": "PWA Android", "platform": "android", "app_version": "1.1.0"})
    assert resp.status_code == 201
    assert resp.json()["device"]["name"] == "PWA Android"
    assert await _count(test_db, SyncDevice, SyncDevice.id == device_id) == 1

    # membro só vê os próprios; dono vê todos
    member = User(id=uuid.uuid4(), tenant_id=tenant_id, email="membro@firma-a.com",
                  hashed_password=get_password_hash("x12345678"), role=UserRole.MEMBER, is_active=True)
    test_db.add(member)
    await test_db.commit()
    member_id = member.id
    member_headers = {"Authorization": "Bearer " + create_access_token(str(member_id), str(tenant_id), "member"),
                      "X-Tenant-ID": str(tenant_id)}
    member_device, _t = _register(http, member_headers)

    owner_list = http.get("/api/v1/sync/devices").json()
    assert {d["id"] for d in owner_list} == {str(device_id), str(member_device)}
    member_list = http.get("/api/v1/sync/devices", headers=member_headers).json()
    assert [d["id"] for d in member_list] == [str(member_device)]

    # membro não revoga dispositivo do dono; revoga o próprio
    assert http.post(f"/api/v1/sync/devices/{device_id}/revoke", headers=member_headers).status_code == 403
    assert http.post(f"/api/v1/sync/devices/{member_device}/revoke", headers=member_headers).status_code == 200

    # id já usado por outro usuário → 409; dispositivo revogado não reativa → 409
    assert http.post("/api/v1/sync/devices", json={
        "id": str(device_id), "name": "x", "platform": "web"}, headers=member_headers).status_code == 409
    assert http.post("/api/v1/sync/devices", json={
        "id": str(member_device), "name": "x", "platform": "web"}, headers=member_headers).status_code == 409

    actions = set((await test_db.execute(
        select(AuditEvent.action).where(AuditEvent.tenant_id == tenant_id))).scalars())
    assert {"sync.device.register", "sync.device.revoke"} <= actions
    assert owner_id is not None


async def test_token_de_usuario_comum_nao_acessa_push_nem_pull(ctx):
    http = ctx["http"]  # headers padrão = token de usuário
    ev = _event(ctx["device_id"], "client", uuid.uuid4(), "create", {"name": "Cliente X"})
    assert http.post("/api/v1/sync/push", json={"events": [ev]}).status_code == 401
    assert http.get("/api/v1/sync/pull?entity=clients").status_code == 401
    # e o token de dispositivo não vale na API comum
    assert http.get("/api/v1/clients", headers=ctx["headers"]).status_code == 401


async def test_renovacao_do_token_de_dispositivo(ctx):
    http = ctx["http"]
    resp = http.post("/api/v1/sync/devices/token", headers=ctx["headers"])
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["tenant_id"] == str(ctx["tenant_id"])
    novo = _dev_headers(body["device_token"], ctx["tenant_id"])
    assert http.get("/api/v1/sync/pull?entity=clients", headers=novo).status_code == 200
    comum = {"Authorization": f"Bearer {body['access_token']}", "X-Tenant-ID": str(ctx["tenant_id"])}
    assert http.get("/api/v1/clients", headers=comum).status_code == 200


async def test_dispositivo_revogado_outro_tenant_e_outro_device(ctx, client_with_auth_b, test_db):
    http = ctx["http"]
    # evento com device_id de outro dispositivo → rejected (sem gravar)
    alheio = _event(uuid.uuid4(), "client", uuid.uuid4(), "create", {"name": "Cliente Y"})
    resp = _push(http, ctx["headers"], alheio)
    assert resp.status_code == 200
    assert resp.json()["acks"][0]["status"] == "rejected"

    # token de dispositivo do escritório B com X-Tenant-ID de A → recusado
    http_b, user_b, _cb, _db = client_with_auth_b
    tenant_b, user_b_id = user_b.tenant_id, user_b.id
    device_b, token_b = _register(http_b)
    assert http.get("/api/v1/sync/pull?entity=clients",
                    headers=_dev_headers(token_b, ctx["tenant_id"])).status_code in (401, 403)
    # token forjado com tenant A para dispositivo de B → 401
    forjado = create_device_token(str(user_b_id), str(ctx["tenant_id"]), "member", str(device_b))
    assert http.get("/api/v1/sync/pull?entity=clients",
                    headers=_dev_headers(forjado, ctx["tenant_id"])).status_code == 401
    assert tenant_b != ctx["tenant_id"]

    # revogado → 401 device_revoked
    assert http.post(f"/api/v1/sync/devices/{ctx['device_id']}/revoke").status_code == 200
    resp = http.get("/api/v1/sync/pull?entity=clients", headers=ctx["headers"])
    assert resp.status_code == 401
    assert resp.json()["code"] == "device_revoked"
    resp = _push(http, ctx["headers"], _event(ctx["device_id"], "client", uuid.uuid4(), "create", {"name": "Z Z"}))
    assert resp.status_code == 401 and resp.json()["code"] == "device_revoked"


async def test_troca_de_senha_derruba_token_de_dispositivo(ctx, test_db):
    user = await test_db.get(User, ctx["user_id"])
    user.tokens_valid_after = datetime.now(timezone.utc) + timedelta(seconds=5)
    await test_db.commit()
    resp = ctx["http"].get("/api/v1/sync/pull?entity=clients", headers=ctx["headers"])
    assert resp.status_code == 401


# ---------------------------------------------------------------------------
# push
# ---------------------------------------------------------------------------


async def test_push_idempotente_aplica_uma_vez(ctx, test_db):
    http, headers = ctx["http"], ctx["headers"]
    entity_id = uuid.uuid4()
    ev = _event(ctx["device_id"], "client", entity_id, "create",
                {"name": "Cliente Offline", "tenant_id": str(uuid.uuid4())})
    first = _push(http, headers, ev)
    assert first.status_code == 200, first.text
    ack1 = first.json()["acks"][0]
    assert ack1["status"] == "ack"
    assert ack1["entity"]["id"] == str(entity_id)
    assert ack1["entity"]["tenant_id"] == str(ctx["tenant_id"])  # tenant do token, nunca do payload
    assert ack1["entity"]["version"] == 1

    second = _push(http, headers, ev)
    ack2 = second.json()["acks"][0]
    assert ack2["status"] == "ack"
    assert ack2["entity"]["id"] == ack1["entity"]["id"]
    assert ack2["entity"]["version"] == 1
    assert await _count(test_db, AccountingClient, AccountingClient.id == entity_id) == 1
    assert await _count(test_db, SyncEvent, SyncEvent.event_id == uuid.UUID(ev["id"])) == 1
    assert await _count(test_db, AuditEvent, AuditEvent.action == "sync.client.create") == 1

    # rejeição repetida devolve a mesma rejeição
    ruim = _event(ctx["device_id"], "client", uuid.uuid4(), "create", {"name": "X"})
    r1 = _push(http, headers, ruim).json()["acks"][0]
    r2 = _push(http, headers, ruim).json()["acks"][0]
    assert r1["status"] == r2["status"] == "rejected"
    assert r1["error"] == r2["error"] and r1["error"].startswith("Dados inválidos")


async def test_rejeicao_nao_desfaz_evento_anterior_do_lote(ctx, test_db):
    a, b = uuid.uuid4(), uuid.uuid4()
    resp = _push(ctx["http"], ctx["headers"],
                 _event(ctx["device_id"], "client", a, "create", {"name": "Cliente Bom"}),
                 _event(ctx["device_id"], "client", b, "create", {"name": ""}))
    acks = resp.json()["acks"]
    assert [x["status"] for x in acks] == ["ack", "rejected"]
    assert await _count(test_db, AccountingClient, AccountingClient.id == a) == 1
    assert await _count(test_db, AccountingClient, AccountingClient.id == b) == 0


async def test_conflito_lww_por_campo(ctx, test_db):
    http = ctx["http"]
    entity_id = uuid.uuid4()
    _push(http, ctx["headers"], _event(ctx["device_id"], "client", entity_id, "create", {"name": "Cliente Base"}))
    dev2, token2 = _register(http, name="PWA Android")
    headers2 = _dev_headers(token2, ctx["tenant_id"])

    # dispositivo 1 edita o nome a partir da versão 1
    r1 = _push(http, ctx["headers"], _event(ctx["device_id"], "client", entity_id, "update",
                                            {"name": "Nome do Dispositivo 1"}, base_version=1)).json()["acks"][0]
    assert r1["status"] == "ack" and r1["entity"]["version"] == 2 and "conflict" not in r1

    # dispositivo 2, ainda na versão 1, edita nome e telefone
    r2 = _push(http, headers2, _event(dev2, "client", entity_id, "update",
                                      {"phone": "11999990000", "notes": "nota do 2"}, base_version=1)).json()["acks"][0]
    assert r2["status"] == "ack"
    assert r2["entity"]["name"] == "Nome do Dispositivo 1"   # campo do servidor preservado
    assert r2["entity"]["phone"] == "11999990000"            # campo do evento aplicado
    assert r2["entity"]["version"] == 3

    # conflito real: dispositivo 2 sobrescreve o nome com base antiga
    r3 = _push(http, headers2, _event(dev2, "client", entity_id, "update",
                                      {"name": "Nome do Dispositivo 2"}, base_version=1)).json()["acks"][0]
    assert r3["conflict"] is True
    assert r3["fields_overwritten"] == {"name": {"server": "Nome do Dispositivo 1", "client": "Nome do Dispositivo 2"}}
    assert r3["entity"]["phone"] == "11999990000"
    conflicts = (await test_db.execute(
        select(SyncConflict).where(SyncConflict.entity_id == entity_id))).scalars().all()
    assert any(c.fields_overwritten.get("name", {}).get("server") == "Nome do Dispositivo 1" for c in conflicts)
    assert all(c.server_version > c.base_version for c in conflicts)


async def test_delete_vira_status_terminal_e_nao_regride(ctx, test_db):
    http, headers, dev = ctx["http"], ctx["headers"], ctx["device_id"]
    client_id = ctx["client_id"]
    ack = _push(http, headers, _event(dev, "client", client_id, "delete")).json()["acks"][0]
    assert ack["status"] == "ack" and ack["entity"]["status"] == "inactive"

    back = _push(http, headers, _event(dev, "client", client_id, "update", {"status": "active"})).json()["acks"][0]
    assert back["status"] == "rejected"
    assert "não pode voltar" in back["error"]

    # honorário pago não é cancelado
    rec_id = uuid.uuid4()
    _push(http, headers, _event(dev, "receivable", rec_id, "create", {
        "client_id": str(client_id), "description": "Honorário", "amount": "300.00",
        "due_date": date.today().isoformat()}))
    pago = _push(http, headers, _event(dev, "receivable", rec_id, "update", {"status": "paid"})).json()["acks"][0]
    assert pago["entity"]["status"] == "paid" and pago["entity"]["paid_at"]
    cancel = _push(http, headers, _event(dev, "receivable", rec_id, "delete")).json()["acks"][0]
    assert cancel["status"] == "rejected"

    # prazo: delete → cancelled
    dl = uuid.uuid4()
    _push(http, headers, _event(dev, "deadline", dl, "create", {
        "client_id": str(client_id), "title": "DCTFWeb", "due_date": date.today().isoformat()}))
    ack = _push(http, headers, _event(dev, "deadline", dl, "delete")).json()["acks"][0]
    assert ack["entity"]["status"] == "cancelled"


async def test_create_com_cliente_de_outro_escritorio_e_rejeitado(ctx, client_b):
    client_b_id = client_b.id
    ack = _push(ctx["http"], ctx["headers"], _event(ctx["device_id"], "deadline", uuid.uuid4(), "create", {
        "client_id": str(client_b_id), "title": "DAS", "due_date": date.today().isoformat()})).json()["acks"][0]
    assert ack["status"] == "rejected"
    assert ack["error"] == "Cliente não encontrado neste escritório."


async def test_erro_transitorio_devolve_503_sem_gravar_rejected(ctx, test_db, monkeypatch):
    from app.api.v1.endpoints import sync as sync_module

    original = sync_module._apply
    calls = {"n": 0}

    async def flaky(db, c, ev):
        calls["n"] += 1
        if calls["n"] == 2:
            raise OperationalError("SELECT 1", {}, Exception("connection reset"))
        return await original(db, c, ev)

    monkeypatch.setattr(sync_module, "_apply", flaky)
    a, b, c3 = uuid.uuid4(), uuid.uuid4(), uuid.uuid4()
    evs = [_event(ctx["device_id"], "client", eid, "create", {"name": f"Cliente {i}"})
           for i, eid in enumerate((a, b, c3))]
    resp = _push(ctx["http"], ctx["headers"], *evs)
    assert resp.status_code == 503
    body = resp.json()
    assert [x["status"] for x in body["acks"]] == ["ack"]
    assert "SELECT" not in body["error"]
    assert await _count(test_db, SyncEvent, SyncEvent.status == "rejected") == 0
    assert await _count(test_db, SyncEvent, SyncEvent.event_id == uuid.UUID(evs[1]["id"])) == 0

    # reenvio do lote inteiro: o primeiro volta como ACK idempotente, o resto aplica
    retry = _push(ctx["http"], ctx["headers"], *evs)
    assert [x["status"] for x in retry.json()["acks"]] == ["ack", "ack", "ack"]
    assert await _count(test_db, AccountingClient, AccountingClient.id.in_([a, b, c3])) == 3


# ---------------------------------------------------------------------------
# regra fiscal (nota)
# ---------------------------------------------------------------------------


async def test_regra_fiscal_da_nota(ctx, test_db):
    issuer = InvoiceIssuer(tenant_id=ctx["tenant_id"], cnpj="10000000000145", regime_tributario="simples",
                           municipio_ibge="3550308")
    test_db.add(issuer)
    await test_db.commit()
    issuer_id = issuer.id
    http, headers, dev = ctx["http"], ctx["headers"], ctx["device_id"]
    base = {"issuer_id": str(issuer_id), "client_id": str(ctx["client_id"]),
            "competencia": date.today().isoformat(), "valor_servico": "500.00",
            "descricao_servico": "Consultoria tributária"}

    emitida = _push(http, headers, _event(dev, "invoice", uuid.uuid4(), "create",
                                          {**base, "status": "issued"})).json()["acks"][0]
    assert emitida["status"] == "rejected"
    numero = _push(http, headers, _event(dev, "invoice", uuid.uuid4(), "create",
                                         {**base, "numero": "123"})).json()["acks"][0]
    assert numero["status"] == "rejected"

    inv_id = uuid.uuid4()
    draft = _push(http, headers, _event(dev, "invoice", inv_id, "create", base)).json()["acks"][0]
    assert draft["status"] == "ack" and draft["entity"]["status"] == "draft"
    assert "xml_content" not in draft["entity"]

    upd = _push(http, headers, _event(dev, "invoice", inv_id, "update", {"status": "issued"})).json()["acks"][0]
    assert upd["status"] == "rejected"

    e1 = _push(http, headers, _event(dev, "invoice", inv_id, "emit_requested")).json()["acks"][0]
    assert e1["status"] == "ack"
    dev2, token2 = _register(http, name="Outro")
    e2 = _push(http, _dev_headers(token2, ctx["tenant_id"]),
               _event(dev2, "invoice", inv_id, "emit_requested")).json()["acks"][0]
    assert e2["status"] == "ack"
    queued = await _count(test_db, InvoiceEvent, InvoiceEvent.invoice_id == inv_id, InvoiceEvent.event_type == "queued")
    assert queued == 1


async def test_emissao_offline_com_mock_em_producao_fica_rascunho(ctx, test_db, monkeypatch):
    """Mesmo portão do POST /emit: mock em produção recusa e a nota segue draft (G2)."""
    from app.core.config import settings

    issuer = InvoiceIssuer(tenant_id=ctx["tenant_id"], cnpj="10000000000145", regime_tributario="simples",
                           municipio_ibge="3550308")
    test_db.add(issuer)
    await test_db.commit()
    http, headers, dev = ctx["http"], ctx["headers"], ctx["device_id"]
    inv_id = uuid.uuid4()
    base = {"issuer_id": str(issuer.id), "client_id": str(ctx["client_id"]),
            "competencia": date.today().isoformat(), "valor_servico": "500.00",
            "descricao_servico": "Consultoria tributária"}
    assert _push(http, headers, _event(dev, "invoice", inv_id, "create", base)).json()["acks"][0]["status"] == "ack"

    monkeypatch.setattr(settings, "NFSE_PROVIDER", "mock")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    ack = _push(http, headers, _event(dev, "invoice", inv_id, "emit_requested")).json()["acks"][0]
    assert ack["status"] == "rejected"
    assert "não configurada" in ack["error"]
    test_db.expire_all()
    inv = (await test_db.execute(select(Invoice).where(Invoice.id == inv_id))).scalar_one()
    assert inv.status == "draft"
    assert await _count(test_db, InvoiceEvent, InvoiceEvent.invoice_id == inv_id,
                        InvoiceEvent.event_type == "queued") == 0


# ---------------------------------------------------------------------------
# pull
# ---------------------------------------------------------------------------


async def test_pull_paginado_com_cursor_e_marca_dagua(ctx, test_db, client_b):
    tenant_id = ctx["tenant_id"]
    client_b_id = client_b.id
    old = datetime(2026, 1, 1, 12, 0, 0, 123456, tzinfo=timezone.utc)
    expected = []
    for i in range(7):
        ts = old + timedelta(minutes=i // 2)  # pares com o mesmo updated_at (desempate pelo id)
        row = AccountingClient(id=uuid.uuid4(), tenant_id=tenant_id, name=f"Pull {i}", entity_type="pj",
                               status="active", client_code=f"9{i:03d}", created_at=ts, updated_at=ts)
        test_db.add(row)
        expected.append((ts, row.id))
    fixture_client = await test_db.get(AccountingClient, ctx["client_id"])
    fixture_client.updated_at = datetime.now(timezone.utc)  # dentro da marca d'água: não sai
    other = await test_db.get(AccountingClient, client_b_id)
    other.updated_at = old
    await test_db.commit()
    expected_ids = [str(i) for _ts, i in sorted(expected)]

    seen, params, pages = [], {"entity": "clients", "limit": 3}, 0
    while True:
        resp = ctx["http"].get("/api/v1/sync/pull", params=params, headers=ctx["headers"])
        assert resp.status_code == 200, resp.text
        body = resp.json()
        seen += [r["id"] for r in body["rows"]]
        assert all("version" in r for r in body["rows"])
        pages += 1
        if not body["has_more"]:
            break
        params = {**params, "since": body["next"]["since"], "after_id": body["next"]["after_id"]}
    assert seen == expected_ids
    assert pages == 3
    assert str(ctx["client_id"]) not in seen and str(client_b_id) not in seen

    # cursor no fim: nada novo
    vazio = ctx["http"].get("/api/v1/sync/pull", params=params, headers=ctx["headers"]).json()
    assert vazio["rows"][-1]["id"] == expected_ids[-1] if vazio["rows"] else True


async def test_pull_de_outro_escritorio_vem_vazio(ctx, client_with_auth_b, test_db):
    http_b, user_b, _cb, _db = client_with_auth_b
    tenant_b = user_b.tenant_id
    old = datetime(2026, 1, 1, tzinfo=timezone.utc)
    row = await test_db.get(AccountingClient, ctx["client_id"])
    row.updated_at = old
    await test_db.commit()
    _dev, token_b = _register(http_b)
    resp = http_b.get("/api/v1/sync/pull?entity=clients", headers=_dev_headers(token_b, tenant_b))
    assert resp.status_code == 200
    assert str(ctx["client_id"]) not in [r["id"] for r in resp.json()["rows"]]
    for entity in ("deadlines", "certificates", "receivables", "invoices"):
        r = http_b.get(f"/api/v1/sync/pull?entity={entity}", headers=_dev_headers(token_b, tenant_b))
        assert r.status_code == 200 and r.json()["has_more"] is False


# ---------------------------------------------------------------------------
# version via REST e retenção
# ---------------------------------------------------------------------------


async def test_version_incrementa_no_patch_rest(client_with_auth_a, test_db):
    http, _user, client_row, _db = client_with_auth_a
    client_id = client_row.id
    assert (await test_db.get(AccountingClient, client_id)).version == 1
    resp = http.patch(f"/api/v1/clients/{client_id}", json={"name": "Nome Novo REST"})
    assert resp.status_code == 200
    row = (await test_db.execute(select(AccountingClient.version).where(AccountingClient.id == client_id))).scalar_one()
    assert row == 2
    http.patch(f"/api/v1/clients/{client_id}", json={"notes": "outra edição"})
    row = (await test_db.execute(select(AccountingClient.version).where(AccountingClient.id == client_id))).scalar_one()
    assert row == 3


async def test_retencao_apaga_sync_events_antigos(ctx, test_db):
    from app.services import scheduler

    dev = ctx["device_id"]
    novo, velho = uuid.uuid4(), uuid.uuid4()
    for eid, received in ((novo, datetime.now(timezone.utc)),
                          (velho, datetime.now(timezone.utc) - timedelta(days=91))):
        test_db.add(SyncEvent(tenant_id=ctx["tenant_id"], device_id=dev, event_id=eid,
                              idempotency_key=f"{dev}:{eid}", entity_type="client", entity_id=uuid.uuid4(),
                              operation="update", payload={}, status="applied", received_at=received))
    await test_db.commit()
    await scheduler.purge_sync_events_scheduled()
    remaining = set((await test_db.execute(select(SyncEvent.event_id))).scalars())
    assert novo in remaining and velho not in remaining
    assert "purge_sync_events" in scheduler.due_job_ids(datetime(2026, 11, 4, 7, 30, tzinfo=timezone.utc))
