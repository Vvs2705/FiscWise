"""Solicitações de ajuste fiscal, regra geral da equipe FiscWise e base de conhecimento com arquivo.

Regras (decisão do dono, 14/11/2026):
- feriado/prazo vale na hora só para o escritório que pediu, na UF/município;
- regra geral vale para todos, mas só na UF/município da regra;
- feriado municipal não mexe em prazo federal nem estadual.
"""

import uuid
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.domain.obligations.business_days import today_br
from app.models.obligation import ObligationInstance, ObligationRule
from app.models.operations import AccountingClient
from app.services.ajustes_fiscais import feriados_extras, parametros_de_vencimento, prazo_ajustado
from app.services.obligation_engine import compute_due_date

SAO_PAULO = "3550308"
CAMPINAS = "3509502"


def _competencia() -> date:
    hoje = today_br()
    return date(hoje.year, hoje.month, 1)


async def _regra(db, code: str, jurisdiction: str, due_day: int) -> ObligationRule:
    r = ObligationRule(
        id=uuid.uuid4(), code=code, name=f"Regra {code}", jurisdiction=jurisdiction,
        recurrence="monthly", due_day=due_day, active=True, requires_employees=False,
    )
    db.add(r)
    await db.commit()
    return r


async def _cliente(db, tenant_id, nome, uf, municipio) -> AccountingClient:
    c = AccountingClient(
        id=uuid.uuid4(), tenant_id=tenant_id, name=nome, document=uuid.uuid4().hex[:14],
        entity_type="pj", status="active", uf=uf, municipio_ibge=municipio,
    )
    db.add(c)
    await db.commit()
    return c


async def _instancia(db, client: AccountingClient, rule: ObligationRule) -> ObligationInstance:
    comp = _competencia()
    due = compute_due_date(rule, comp.year, comp.month, uf=client.uf, municipio_ibge=client.municipio_ibge)
    inst = ObligationInstance(
        id=uuid.uuid4(), tenant_id=client.tenant_id, client_id=client.id, rule_id=rule.id,
        competence_month=comp, due_date=due, status="pending", priority="medium",
    )
    db.add(inst)
    await db.commit()
    return inst


async def _due(db, inst) -> date:
    await db.refresh(inst)
    return inst.due_date


@pytest.fixture
def equipe_b(client_with_auth_b):
    """Usuário B vira equipe FiscWise (o flag basta; o escritório dele não importa)."""
    http_b, user_b, client_b, db = client_with_auth_b
    user_b.equipe_fiscwise = True
    return http_b, user_b, db


# ─── Funções puras ───────────────────────────────────────────────────────────

def test_feriado_recorrente_e_niveis():
    a_mun = SimpleNamespace(tipo="feriado", mes=1, dia=25, ano=None, municipio_ibge=SAO_PAULO, nome="Aniv")
    a_uf = SimpleNamespace(tipo="feriado", mes=7, dia=9, ano=2026, municipio_ibge=None, nome="Rev")
    extras = feriados_extras([a_mun, a_uf], [2026, 2027])
    assert extras[date(2026, 1, 25)] == ("Aniv", "municipio")
    assert extras[date(2027, 1, 25)] == ("Aniv", "municipio")
    assert extras[date(2026, 7, 9)] == ("Rev", "uf")
    assert date(2027, 7, 9) not in extras  # ano fixo


def test_prazo_mais_especifico_vence():
    t = uuid.uuid4()
    geral_uf = SimpleNamespace(tipo="prazo", due_day=15, obrigacao_code="ISS", municipio_ibge=None, tenant_id=None)
    esc_uf = SimpleNamespace(tipo="prazo", due_day=12, obrigacao_code="ISS", municipio_ibge=None, tenant_id=t)
    geral_mun = SimpleNamespace(tipo="prazo", due_day=8, obrigacao_code="iss", municipio_ibge=SAO_PAULO, tenant_id=None)
    assert prazo_ajustado([geral_uf, esc_uf], "ISS") == 12
    assert prazo_ajustado([geral_uf, esc_uf, geral_mun], "ISS") == 8
    assert prazo_ajustado([geral_uf], "DAS") is None


def test_feriado_municipal_nao_move_prazo_federal_nem_estadual():
    comp = date(2026, 3, 1)
    for code, jur in (("FED-T", "federal"), ("EST-T", "estadual"), ("MUN-T", "municipal")):
        rule = SimpleNamespace(code=code, jurisdiction=jur, recurrence="monthly", due_day=10, state=None)
        base = compute_due_date(rule, 2026, 3, uf="SP", municipio_ibge=SAO_PAULO)
        aj = SimpleNamespace(tipo="feriado", mes=base.month, dia=base.day, ano=base.year,
                             municipio_ibge=SAO_PAULO, uf="SP", nome="Feriado", tenant_id=None,
                             obrigacao_code=None, due_day=None)
        override, extras = parametros_de_vencimento([aj], code, "SP", SAO_PAULO, comp)
        novo = compute_due_date(rule, 2026, 3, uf="SP", municipio_ibge=SAO_PAULO,
                                due_day_override=override, extra_holidays=extras)
        if jur == "municipal":
            assert novo < base
        else:
            assert novo == base


def test_migracao_forca_rls_nas_tabelas_novas():
    p = Path(__file__).parents[1] / "alembic" / "versions" / "v8x9ajustes_solicitacoes_ajuste_fiscal.py"
    txt = p.read_text(encoding="utf-8")
    for tabela in ("fiscal_adjustment_requests", "fiscal_calendar_adjustments"):
        assert f"ALTER TABLE {tabela} ENABLE ROW LEVEL SECURITY" in txt
        assert f"ALTER TABLE {tabela} FORCE ROW LEVEL SECURITY" in txt
        assert f"CREATE POLICY tenant_isolation ON {tabela}" in txt


# ─── Escritório ──────────────────────────────────────────────────────────────

async def test_feriado_municipal_vale_so_no_municipio_e_no_escritorio(client_with_auth_a, client_with_auth_b):
    http_a, user_a, client_a, db = client_with_auth_a
    _, _, client_b, _ = client_with_auth_b
    regra = await _regra(db, "MUN-TESTE", "municipal", 10)
    cli_sp = await _cliente(db, user_a.tenant_id, "Cliente SP", "SP", SAO_PAULO)
    cli_camp = await _cliente(db, user_a.tenant_id, "Cliente Campinas", "SP", CAMPINAS)
    cli_b_sp = await _cliente(db, client_b.tenant_id, "Cliente B SP", "SP", SAO_PAULO)
    i_sp = await _instancia(db, cli_sp, regra)
    i_camp = await _instancia(db, cli_camp, regra)
    i_b = await _instancia(db, cli_b_sp, regra)
    base = i_sp.due_date

    r = http_a.post("/api/v1/ajustes-fiscais", json={
        "tipo": "feriado", "uf": "sp", "municipio_ibge": SAO_PAULO, "municipio_nome": "São Paulo",
        "data": base.isoformat(), "descricao": "Feriado municipal que faltava",
    })
    assert r.status_code == 201, r.text
    out = r.json()
    assert out["status"] == "aplicada_no_escritorio"
    assert out["recalculadas"] == 1
    assert await _due(db, i_sp) < base
    assert await _due(db, i_camp) == i_camp.due_date
    assert await _due(db, i_b) == base  # outro escritório não muda

    ativos = http_a.get("/api/v1/ajustes-fiscais/ajustes-ativos").json()
    assert [a["escopo"] for a in ativos] == ["escritorio"]

    # Desfazer volta o vencimento.
    d = http_a.delete(f"/api/v1/ajustes-fiscais/{out['id']}")
    assert d.status_code == 200, d.text
    assert await _due(db, i_sp) == base
    assert http_a.get("/api/v1/ajustes-fiscais").json() == []


async def test_prazo_por_uf(client_with_auth_a):
    http_a, user_a, _, db = client_with_auth_a
    regra = await _regra(db, "EST-TESTE", "estadual", 20)
    cli = await _cliente(db, user_a.tenant_id, "Cliente SP", "SP", SAO_PAULO)
    cli_rj = await _cliente(db, user_a.tenant_id, "Cliente RJ", "RJ", "3304557")
    i = await _instancia(db, cli, regra)
    i_rj = await _instancia(db, cli_rj, regra)

    r = http_a.post("/api/v1/ajustes-fiscais", json={
        "tipo": "prazo", "uf": "SP", "obrigacao_code": "est-teste", "due_day": 5,
        "descricao": "ICMS em SP vence dia 5",
    })
    assert r.status_code == 201, r.text
    comp = _competencia()
    esperado = compute_due_date(regra, comp.year, comp.month, uf="SP", due_day_override=5)
    assert await _due(db, i) == esperado
    assert await _due(db, i_rj) == i_rj.due_date


async def test_validacoes_e_permissoes(client_with_auth_a, client_with_auth_b):
    http_a, *_ = client_with_auth_a
    http_b, *_ = client_with_auth_b
    base = {"descricao": "Teste de validação"}
    assert http_a.post("/api/v1/ajustes-fiscais", json={**base, "tipo": "feriado", "uf": "SP"}).status_code == 422
    assert http_a.post("/api/v1/ajustes-fiscais", json={**base, "tipo": "prazo", "uf": "SP", "obrigacao_code": "X"}).status_code == 422
    assert http_a.post("/api/v1/ajustes-fiscais", json={**base, "tipo": "outro", "uf": "XX"}).status_code == 422
    assert http_a.post("/api/v1/ajustes-fiscais", json={**base, "tipo": "outro", "uf": "SP", "municipio_ibge": "123"}).status_code == 422
    assert http_a.post("/api/v1/ajustes-fiscais", json={**base, "tipo": "invalido", "uf": "SP"}).status_code == 422
    # Membro (não gestor) não cria.
    assert http_b.post("/api/v1/ajustes-fiscais", json={**base, "tipo": "outro", "uf": "BA"}).status_code == 403
    # Não-equipe não entra na área da equipe.
    assert http_a.get("/api/v1/equipe/ajustes-fiscais").status_code == 403


async def test_escritorio_nao_ve_solicitacao_de_outro(client_with_auth_a, client_with_auth_b):
    http_a, *_ = client_with_auth_a
    http_b, *_ = client_with_auth_b
    r = http_a.post("/api/v1/ajustes-fiscais", json={
        "tipo": "nova_obrigacao", "uf": "BA", "descricao": "Nova declaração estadual na Bahia",
    })
    assert r.status_code == 201, r.text
    assert r.json()["status"] == "em_analise"
    sid = r.json()["id"]
    assert http_b.get(f"/api/v1/ajustes-fiscais/{sid}").status_code == 404
    assert http_b.get("/api/v1/ajustes-fiscais").json() == []


# ─── Equipe FiscWise ─────────────────────────────────────────────────────────

async def test_regra_geral_vale_para_todos_so_no_municipio(client_with_auth_a, equipe_b):
    http_a, user_a, _, db = client_with_auth_a
    http_eq, user_eq, _ = equipe_b
    regra = await _regra(db, "MUN-GERAL", "municipal", 10)
    cli_a = await _cliente(db, user_a.tenant_id, "A SP", "SP", SAO_PAULO)
    cli_b = await _cliente(db, user_eq.tenant_id, "B SP", "SP", SAO_PAULO)
    cli_b_ba = await _cliente(db, user_eq.tenant_id, "B BA", "BA", "2927408")
    i_a = await _instancia(db, cli_a, regra)
    i_b = await _instancia(db, cli_b, regra)
    i_ba = await _instancia(db, cli_b_ba, regra)
    base = i_a.due_date

    sid = http_a.post("/api/v1/ajustes-fiscais", json={
        "tipo": "feriado", "uf": "SP", "municipio_ibge": SAO_PAULO, "data": base.isoformat(),
        "recorrente_anual": True, "descricao": "Feriado municipal de SP",
    }).json()["id"]
    assert await _due(db, i_b) == base  # ainda só do escritório A

    lista = http_eq.get("/api/v1/equipe/ajustes-fiscais", params={"uf": "SP"}).json()
    assert [x["id"] for x in lista] == [sid]
    assert lista[0]["tenant_name"]

    r = http_eq.post(f"/api/v1/equipe/ajustes-fiscais/{sid}/regra-geral", json={"resposta": "Confirmado."})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "regra_geral"
    assert await _due(db, i_b) < base          # outro escritório no mesmo município
    assert await _due(db, i_ba) == i_ba.due_date  # outra UF não muda

    # Escritório A vê o resultado e o ajuste geral.
    assert http_a.get(f"/api/v1/ajustes-fiscais/{sid}").json()["status"] == "regra_geral"
    escopos = {a["escopo"] for a in http_a.get("/api/v1/ajustes-fiscais/ajustes-ativos").json()}
    assert escopos == {"escritorio", "geral"}


async def test_equipe_recusa_e_tipo_livre_nao_vira_regra(client_with_auth_a, equipe_b):
    http_a, *_ = client_with_auth_a
    http_eq, _, _ = equipe_b
    sid = http_a.post("/api/v1/ajustes-fiscais", json={
        "tipo": "outro", "uf": "MG", "descricao": "Regra local de Belo Horizonte",
    }).json()["id"]
    assert http_eq.post(f"/api/v1/equipe/ajustes-fiscais/{sid}/regra-geral").status_code == 422
    assert http_eq.post(f"/api/v1/equipe/ajustes-fiscais/{sid}/recusar", json={"resposta": "ok"}).status_code == 422
    r = http_eq.post(f"/api/v1/equipe/ajustes-fiscais/{sid}/recusar", json={"resposta": "Já está no calendário."})
    assert r.status_code == 200 and r.json()["status"] == "recusada"
    assert http_a.get(f"/api/v1/ajustes-fiscais/{sid}").json()["resposta_equipe"] == "Já está no calendário."


# ─── Base de conhecimento com arquivo ────────────────────────────────────────

async def test_upload_txt_anexo_e_visao_da_equipe(client_with_auth_a, equipe_b, monkeypatch):
    from app.core import storage

    http_a, *_ = client_with_auth_a
    http_eq, _, _ = equipe_b
    monkeypatch.setattr(storage, "_storage_configured", lambda: True)
    upload = AsyncMock(return_value="ok")
    monkeypatch.setattr(storage, "upload_bytes", upload)
    monkeypatch.setattr(storage, "get_signed_url", AsyncMock(return_value="https://assinado/arquivo"))

    texto = "Lei municipal 123/2026: o ISS passa a vencer no dia 5. " * 200
    r = http_a.post(
        "/api/v1/rag/documents/upload",
        files={"file": ("lei-iss.txt", texto.encode("utf-8"), "text/plain")},
        data={"title": "Lei do ISS de SP"},
    )
    assert r.status_code == 201, r.text
    doc = r.json()
    assert doc["file_name"] == "lei-iss.txt"
    assert doc["file_size"] == len(texto.encode("utf-8"))
    assert len(doc["content"]) > 5000  # texto inteiro, sem o corte do parser
    assert upload.await_args.args[1].endswith("-lei-iss.txt")

    assert http_a.get(f"/api/v1/rag/documents/{doc['id']}/download").json() == {"url": "https://assinado/arquivo"}

    # Tipo não aceito.
    ruim = http_a.post("/api/v1/rag/documents/upload", files={"file": ("x.exe", b"MZ", "application/octet-stream")},
                       data={"title": "Programa"})
    assert ruim.status_code == 415

    sid = http_a.post("/api/v1/ajustes-fiscais", json={
        "tipo": "outro", "uf": "SP", "descricao": "Nova lei do ISS", "knowledge_doc_id": doc["id"],
    }).json()["id"]
    det = http_eq.get(f"/api/v1/equipe/ajustes-fiscais/{sid}").json()
    assert det["knowledge_doc"]["title"] == "Lei do ISS de SP"
    assert det["knowledge_doc"]["download_url"] == "https://assinado/arquivo"
    assert det["knowledge_doc"]["content_preview"].startswith("Lei municipal 123/2026")


async def test_upload_sem_storage_responde_503(client_with_auth_a, monkeypatch):
    from app.core import storage

    http_a, *_ = client_with_auth_a
    monkeypatch.setattr(storage, "_storage_configured", lambda: False)
    r = http_a.post("/api/v1/rag/documents/upload",
                    files={"file": ("a.txt", b"conteudo de teste", "text/plain")}, data={"title": "Teste"})
    assert r.status_code == 503
