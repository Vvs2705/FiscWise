"""Fila de trabalho em Postgres (background_jobs): enqueue, claim, retry, tick,
endpoints de status, document.parse e invoice.emit."""

import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import httpx
import pytest
from sqlalchemy import select

from app.models.background_job import BackgroundJob
from app.services import job_handlers, job_queue
from app.services.job_queue import (
    JobRetry,
    PermanentJobError,
    claim_next,
    enqueue,
    job_handler,
    run_pending,
)


@pytest.fixture
def registry(monkeypatch):
    """Registry isolado: handlers de teste não vazam entre testes."""
    job_queue._load_handler_modules()
    monkeypatch.setattr(job_queue, "_REGISTRY", dict(job_queue._REGISTRY))
    return job_queue._REGISTRY


async def _jobs(db):
    return (await db.execute(select(BackgroundJob))).scalars().all()


async def test_enqueue_idempotente_por_chave(test_db, tenant_a):
    j1 = await enqueue(test_db, "t.x", {"a": 1}, tenant_a.id, idempotency_key="t.x:1")
    j2 = await enqueue(test_db, "t.x", {"a": 2}, tenant_a.id, idempotency_key="t.x:1")
    await test_db.commit()
    assert j1.id == j2.id
    assert len(await _jobs(test_db)) == 1
    assert j2.payload == {"a": 1}


async def test_enqueue_sem_chave_cria_um_por_chamada(test_db, tenant_a):
    await enqueue(test_db, "t.x", {}, tenant_a.id)
    await enqueue(test_db, "t.x", {}, tenant_a.id)
    await test_db.commit()
    assert len(await _jobs(test_db)) == 2


async def test_claim_sequencial_nao_pega_o_mesmo_job_duas_vezes(test_db, tenant_a):
    a = await enqueue(test_db, "t.x", {}, tenant_a.id)
    b = await enqueue(test_db, "t.x", {}, tenant_a.id)
    futuro = await enqueue(
        test_db, "t.x", {}, tenant_a.id, run_after=datetime.now(timezone.utc) + timedelta(hours=1)
    )
    await test_db.commit()

    c1 = await claim_next(test_db, "w1")
    c2 = await claim_next(test_db, "w2")
    c3 = await claim_next(test_db, "w3")
    assert {c1.id, c2.id} == {a.id, b.id}
    assert c3 is None  # o terceiro só roda daqui a 1 h
    assert c1.status == "running" and c1.attempts == 1 and c1.locked_by == "w1"
    assert futuro.status == "queued"


async def test_job_abandonado_e_reclamado(test_db, tenant_a):
    job = await enqueue(test_db, "t.x", {}, tenant_a.id)
    await test_db.commit()
    claimed = await claim_next(test_db, "morto")
    claimed.locked_at = datetime.now(timezone.utc) - timedelta(minutes=16)
    await test_db.commit()

    again = await claim_next(test_db, "vivo")
    assert again.id == job.id and again.locked_by == "vivo" and again.attempts == 2


async def test_job_abandonado_sem_tentativas_vira_failed(test_db, tenant_a):
    await enqueue(test_db, "t.x", {}, tenant_a.id, max_attempts=1)
    await test_db.commit()
    claimed = await claim_next(test_db, "morto")
    claimed.locked_at = datetime.now(timezone.utc) - timedelta(minutes=16)
    await test_db.commit()

    assert await claim_next(test_db, "vivo") is None
    job = (await _jobs(test_db))[0]
    assert job.status == "failed" and "Abandonado" in job.last_error


async def test_run_pending_sucesso_retry_e_falha_definitiva(test_db, tenant_a, registry):
    calls = {"ok": 0, "flaky": 0}

    @job_handler("t.ok")
    async def ok(ctx):
        calls["ok"] += 1
        return {"n": ctx.payload["n"]}

    @job_handler("t.flaky")
    async def flaky(ctx):
        calls["flaky"] += 1
        raise RuntimeError("serviço fora")

    @job_handler("t.perm")
    async def perm(ctx):
        raise PermanentJobError("dado inválido")

    ok_job = await enqueue(test_db, "t.ok", {"n": 7}, tenant_a.id)
    flaky_job = await enqueue(test_db, "t.flaky", {}, tenant_a.id, max_attempts=2)
    perm_job = await enqueue(test_db, "t.perm", {}, tenant_a.id)
    sem_handler = await enqueue(test_db, "t.desconhecido", {}, tenant_a.id)
    await test_db.commit()

    counts = await run_pending(test_db, max_jobs=10, time_budget_s=30)
    assert counts == {"done": 1, "retry": 1, "failed": 2}

    await test_db.refresh(ok_job)
    await test_db.refresh(flaky_job)
    await test_db.refresh(perm_job)
    await test_db.refresh(sem_handler)
    assert ok_job.status == "done" and ok_job.result == {"n": 7}
    assert flaky_job.status == "queued" and flaky_job.attempts == 1
    assert "serviço fora" in flaky_job.last_error
    assert perm_job.status == "failed" and perm_job.attempts == 1
    assert sem_handler.status == "failed" and "Nenhum handler" in sem_handler.last_error

    # Backoff: não roda de novo antes do run_after.
    assert await run_pending(test_db) == {"done": 0, "retry": 0, "failed": 0}

    # Venceu o backoff: segunda tentativa esgota max_attempts=2 → failed.
    flaky_job.run_after = datetime.now(timezone.utc) - timedelta(seconds=1)
    await test_db.commit()
    assert (await run_pending(test_db))["failed"] == 1
    await test_db.refresh(flaky_job)
    assert flaky_job.status == "failed" and flaky_job.attempts == 2 and calls["flaky"] == 2


async def test_job_retry_usa_atraso_pedido(test_db, tenant_a, registry):
    @job_handler("t.later")
    async def later(ctx):
        raise JobRetry("volta depois", delay_s=3600)

    job = await enqueue(test_db, "t.later", {}, tenant_a.id)
    await test_db.commit()
    antes = datetime.now(timezone.utc)
    await run_pending(test_db)
    await test_db.refresh(job)
    run_after = job.run_after.replace(tzinfo=job.run_after.tzinfo or timezone.utc)
    assert job.status == "queued" and run_after >= antes + timedelta(minutes=59)


def test_backoff_padrao():
    assert [job_queue.retry_delay_seconds(n) for n in (1, 2, 3)] == [60, 300, 1500]


def test_handler_duplicado_e_recusado(registry):
    @job_handler("t.dup")
    async def a(ctx):
        return None

    with pytest.raises(ValueError):
        @job_handler("t.dup")
        async def b(ctx):
            return None


def test_kinds_publicos_registrados():
    assert {"document.parse", "invoice.emit"} <= set(job_queue.registered_kinds())


# ── Endpoints de status (isolamento por escritório) ─────────────────────────

async def test_status_do_job_isolado_por_tenant(client_with_auth_a, tenant_b):
    http, user_a, _client, db = client_with_auth_a
    mine = await enqueue(db, "t.x", {}, user_a.tenant_id)
    other = await enqueue(db, "t.x", {}, tenant_b.id)
    global_job = await enqueue(db, "t.x", {}, None)
    await db.commit()

    r = http.get(f"/api/v1/jobs/{mine.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "queued" and body["attempts"] == 0 and body["last_error"] is None
    assert {"created_at", "updated_at", "kind", "max_attempts"} <= set(body)

    assert http.get(f"/api/v1/jobs/{other.id}").status_code == 404
    assert http.get(f"/api/v1/jobs/{global_job.id}").status_code == 404

    listed = http.get("/api/v1/jobs?status=queued&limit=10").json()
    assert [j["id"] for j in listed] == [str(mine.id)]
    assert http.get("/api/v1/jobs?status=done").json() == []
    assert http.get("/api/v1/jobs?status=xpto").status_code == 422


# ── document.parse ──────────────────────────────────────────────────────────

async def test_upload_enfileira_parse_e_tick_processa(client_with_auth_a, monkeypatch):
    from app.api.v1.endpoints import operations
    from app.models.operations import ClientDocument

    http, _user, client_a, db = client_with_auth_a

    async def fake_upload(bucket, path, data, content_type="application/octet-stream", **kw):
        return path

    async def fake_parse(path, name):
        with open(path, "rb") as fh:
            return {"bytes": len(fh.read())}, None

    async def fake_classify(parsed, **kw):
        return None

    monkeypatch.setattr("app.core.storage.upload_bytes", fake_upload)
    monkeypatch.setattr(operations, "parse_document", fake_parse)
    monkeypatch.setattr(operations, "classify_fiscal_document", fake_classify)

    resp = http.post(
        f"/api/v1/clients/{client_a.id}/documents?document_type=contract",
        files={"file": ("contrato.pdf", b"%PDF-1.7 teste")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["parse_status"] == "processing" and body["job_id"]
    assert {"id", "file_url", "name", "document_type"} <= set(body)  # contrato mantido

    job_id = uuid.UUID(body["job_id"])
    assert http.get(f"/api/v1/jobs/{job_id}").json()["status"] == "queued"

    # "Tick": processa a fila (mesma sessão do teste no SQLite).
    assert (await run_pending(db))["done"] == 1
    doc = (
        await db.execute(
            select(ClientDocument).where(ClientDocument.id == uuid.UUID(body["id"]))
            .execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert doc.parse_status == "completed" and doc.parsed_data == {"bytes": 14}
    status_body = http.get(f"/api/v1/jobs/{job_id}").json()
    assert status_body["status"] == "done"
    assert status_body["result"]["parse_status"] == "completed"


async def test_parse_sem_arquivo_local_nem_storage_marca_documento_failed(test_db, client_a):
    from app.models.operations import ClientDocument

    doc = ClientDocument(
        tenant_id=client_a.tenant_id, client_id=client_a.id, name="x.pdf",
        document_type="contract", file_url="u", status="available", parse_status="processing",
    )
    test_db.add(doc)
    await test_db.flush()
    await enqueue(
        test_db, "document.parse",
        {"document_id": str(doc.id), "storage_path": "p/x.pdf", "file_name": "x.pdf",
         "tmp_path": "/nao/existe.pdf"},
        client_a.tenant_id, idempotency_key=f"document.parse:{doc.id}",
    )
    await test_db.commit()

    assert (await run_pending(test_db))["failed"] == 1
    await test_db.refresh(doc)
    assert doc.parse_status == "failed" and "indisponível" in doc.parse_error


# ── invoice.emit ────────────────────────────────────────────────────────────

async def _queued_invoice(db, tenant_id, client_id):
    from app.domain.invoices.models import Invoice, InvoiceIssuer

    issuer = InvoiceIssuer(
        tenant_id=tenant_id, client_id=client_id, cnpj="11222333000181",
        inscricao_municipal="123", regime_tributario="simples_nacional",
        municipio_ibge="3550308", cod_servico_lc116="01.01", aliquota_iss=Decimal("0.02"),
    )
    db.add(issuer)
    await db.flush()
    inv = Invoice(
        tenant_id=tenant_id, issuer_id=issuer.id, client_id=client_id, status="queued",
        competencia=date.today().replace(day=1), valor_servico=Decimal("100.00"),
        valor_deducoes=Decimal("0"), valor_iss=Decimal("2.00"),
        descricao_servico="Serviço contábil", tomador_nome="Tomador",
    )
    db.add(inv)
    await db.commit()
    return inv


@pytest.fixture
def sem_carencia(monkeypatch):
    monkeypatch.setattr(job_handlers, "INVOICE_SWEEP_GRACE", timedelta(0))


async def test_tick_emite_nota_queued_uma_vez_e_nao_duplica(
    test_db, client_a, sem_carencia, monkeypatch
):
    from app.domain.invoices.providers.mock import MockNfseProvider
    from app.services.scheduler import process_job_queue

    inv = await _queued_invoice(test_db, client_a.tenant_id, client_a.id)
    emits = []

    class CountingProvider(MockNfseProvider):
        async def emit(self, data):
            emits.append(data)
            return await super().emit(data)

    monkeypatch.setattr(job_handlers, "get_emission_provider", CountingProvider)

    first = await process_job_queue()
    assert first["invoices_enqueued"] == 1 and first["jobs"]["done"] == 1
    second = await process_job_queue()
    assert second["invoices_enqueued"] == 0 and second["jobs"] == {"done": 0, "retry": 0, "failed": 0}

    assert len(emits) == 1
    await test_db.refresh(inv)
    assert inv.status == "issued"
    jobs = await _jobs(test_db)
    assert len(jobs) == 1
    assert jobs[0].idempotency_key == f"invoice.emit:{inv.id}"
    assert jobs[0].payload == {"invoice_id": str(inv.id), "tenant_id": str(client_a.tenant_id)}
    assert jobs[0].status == "done"


async def test_emissao_com_erro_transitorio_volta_para_queued_e_agenda_retry(
    client_with_auth_a, sem_carencia, monkeypatch
):
    from app.domain.invoices.models import InvoiceEvent, InvoiceRejection
    from app.domain.invoices.providers.mock import MockNfseProvider
    from app.services.scheduler import process_job_queue

    http, user_a, client_a, db = client_with_auth_a
    inv = await _queued_invoice(db, user_a.tenant_id, client_a.id)

    class Offline(MockNfseProvider):
        async def emit(self, data):
            raise httpx.ConnectError("sem rede")

    monkeypatch.setattr(job_handlers, "get_emission_provider", Offline)
    out = await process_job_queue()
    assert out["jobs"]["retry"] == 1

    await db.refresh(inv)
    assert inv.status == "queued"  # nunca autorizada sem o provedor
    rejections = (await db.execute(select(InvoiceRejection))).scalars().all()
    assert rejections == []
    events = [e.event_type for e in (await db.execute(select(InvoiceEvent))).scalars().all()]
    assert "emit_retry" in events

    job = (await _jobs(db))[0]
    body = http.get(f"/api/v1/jobs/{job.id}").json()
    assert body["status"] == "queued" and body["attempts"] == 1
    assert "Provedor indisponível" in body["last_error"]

    # Varredor seguinte não duplica o job pendente.
    await process_job_queue()
    assert len(await _jobs(db)) == 1


async def test_rejeicao_definitiva_registrada_pelo_dominio(test_db, client_a, sem_carencia):
    from app.domain.invoices.models import InvoiceRejection

    inv = await _queued_invoice(test_db, client_a.tenant_id, client_a.id)
    inv.descricao_servico = "fail_validation"
    await test_db.commit()

    await job_handlers.drain_queued_invoices(test_db)
    assert (await run_pending(test_db))["done"] == 1
    await test_db.refresh(inv)
    assert inv.status == "rejected"
    rej = (await test_db.execute(select(InvoiceRejection))).scalars().all()
    assert [r.codigo_rejeicao for r in rej] == ["E001"]


async def test_handler_ignora_nota_fora_de_queued(test_db, client_a):
    inv = await _queued_invoice(test_db, client_a.tenant_id, client_a.id)
    inv.status = "draft"
    await test_db.commit()
    job = await job_handlers.enqueue_invoice_emit(test_db, inv.id, client_a.tenant_id)
    await test_db.commit()
    await run_pending(test_db)
    await test_db.refresh(job)
    await test_db.refresh(inv)
    assert job.status == "done" and job.result["skipped"] == "draft"
    assert inv.status == "draft"


async def test_varredor_respeita_carencia(test_db, client_a):
    await _queued_invoice(test_db, client_a.tenant_id, client_a.id)
    assert await job_handlers.drain_queued_invoices(test_db) == 0  # nota recém-enfileirada
