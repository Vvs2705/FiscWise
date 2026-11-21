"""Varredura de IDOR entre escritórios (requisito 2 do checklist de compliance).

O escritório B cria os próprios registros pela API; o escritório A tenta ler,
alterar, apagar e acionar cada um deles pelo identificador.

A suíte roda em SQLite, sem RLS: o que é testado aqui é o filtro por
`tenant_id` no código. A RLS do PostgreSQL é a segunda camada
(tests/test_rls_postgres.py, no CI).

Para cada rota de leitura, o próprio B recebe 200 no mesmo registro. Como os
dois escritórios estão no mesmo plano, o 404 de A não vem de bloqueio de
plano, e sim do isolamento. Nas rotas que alteram, o registro de B continua
lá, sem mudança, depois da tentativa de A.
"""

from __future__ import annotations

import base64
import os
import uuid
from datetime import date, datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.domain.certificados import cofre
from app.domain.certificados.models import CertificadoA1
from app.models.user import UserRole

CNPJ_B = "09134865420327"


@pytest.fixture
def chave_cofre(monkeypatch):
    monkeypatch.setattr(
        settings, "CERT_ENCRYPTION_KEY", base64.b64encode(os.urandom(32)).decode(), raising=False
    )


@pytest.fixture
async def dono_b(test_db, user_b, client_b):
    """HTTP do escritório B com perfil OWNER (o user_b padrão é MEMBER)."""
    from fastapi.testclient import TestClient

    from app.core.deps import get_db
    from app.main import app

    user_b.role = UserRole.OWNER
    await test_db.commit()
    app.dependency_overrides[get_db] = lambda: test_db
    http = TestClient(app)
    token = create_access_token(
        user_id=str(user_b.id), tenant_id=str(user_b.tenant_id), role=UserRole.OWNER.value
    )
    http.headers.update({"Authorization": f"Bearer {token}", "X-Tenant-ID": str(user_b.tenant_id)})
    return http


def _ok(r, *codes):
    assert r.status_code in (codes or (200, 201)), f"{r.request.method} {r.request.url}: {r.status_code} {r.text}"
    return r.json()


async def _recursos_de_b(http_b, client_b, test_db, tenant_b_id) -> dict[str, str]:
    """Cria pela API (como B) um registro de cada tipo e devolve os ids."""
    futuro = (date.today() + timedelta(days=20)).isoformat()
    ids: dict[str, str] = {"client_id": str(client_b.id)}

    ids["deadline_id"] = _ok(http_b.post("/api/v1/deadlines", json={
        "client_id": str(client_b.id), "title": "Prazo de B", "category": "fiscal",
        "due_date": futuro, "status": "pending", "priority": "medium",
    }))["id"]
    ids["guia_id"] = _ok(http_b.post("/api/v1/guias", json={
        "client_id": str(client_b.id), "tipo": "DAS", "competencia": date.today().isoformat(),
        "valor": 450.00, "vencimento": futuro,
    }))["id"]
    ids["proxy_id"] = _ok(http_b.post("/api/v1/ecac/proxies", json={
        "outorgante_cpf_cnpj": "10000000000145", "procurador_cpf": "10000000019",
        "data_validade": "2027-01-31",
    }))["id"]
    ids["instance_id"] = _ok(http_b.post("/api/v1/obligations/instances", json={
        "client_id": str(client_b.id), "competence_month": "2026-09-01",
        "due_date": "2026-10-20", "priority": "medium", "custom_name": "Obrigação de B",
    }))["id"]
    ids["key_id"] = _ok(http_b.post("/api/v1/developer/api-keys", json={"name": "Chave de B"}))["id"]
    ids["sub_id"] = _ok(http_b.post("/api/v1/developer/webhooks", json={
        "url": "https://example.com/webhook-b", "events": ["client.created"],
    }))["id"]
    issuer = _ok(http_b.post("/api/v1/invoices/issuers", json={
        "client_id": str(client_b.id), "cnpj": CNPJ_B, "inscricao_municipal": "123456",
        "regime_tributario": "simples", "municipio_ibge": "3550308",
        "cod_servico_lc116": "17.01", "aliquota_iss": "0.02",
    }))
    ids["issuer_id"] = issuer["id"]
    ids["invoice_id"] = _ok(http_b.post("/api/v1/invoices", json={
        "issuer_id": issuer["id"], "client_id": str(client_b.id),
        "competencia": date.today().isoformat(), "valor_servico": 500.00,
        "valor_deducoes": 0.00, "descricao_servico": "Consultoria de B",
    }))["id"]

    # Certificado A1 do escritório B, gravado direto (o envio exige um .pfx
    # ICP-Brasil; o fluxo de envio já tem testes em test_certificados.py).
    cert_id = uuid.uuid4()
    test_db.add(CertificadoA1(
        id=cert_id, tenant_id=tenant_b_id, escopo="escritorio", titular_nome="ESCRITORIO B",
        documento="11222333000181", tipo_documento="cnpj", emissor="AC Teste",
        numero_serie="1", thumbprint_sha256="b" * 64,
        valido_de=datetime.now(timezone.utc) - timedelta(days=1),
        valido_ate=datetime.now(timezone.utc) + timedelta(days=365),
        pfx_cifrado=cofre.cifrar(b"pfx", tenant_id=tenant_b_id, certificado_id=cert_id, campo="pfx"),
        senha_cifrada=cofre.cifrar(b"senha", tenant_id=tenant_b_id, certificado_id=cert_id, campo="senha"),
    ))
    await test_db.commit()
    ids["cert_id"] = str(cert_id)
    return ids


# Rotas de leitura: B recebe 200 no próprio registro, A não pode receber 2xx.
LEITURAS = [
    "/api/v1/clients/{client_id}",
    "/api/v1/clients/{client_id}/billing-config",
    "/api/v1/clients/{client_id}/billing-history",
    "/api/v1/clients/{client_id}/documents",
    "/api/v1/clients/{client_id}/partners",
    "/api/v1/clients/{client_id}/company-documents",
    "/api/v1/deadlines/{deadline_id}",
    "/api/v1/guias/{guia_id}",
    "/api/v1/ecac/proxies/{proxy_id}",
    "/api/v1/invoices/{invoice_id}",
    "/api/v1/invoices/{invoice_id}/events",
    "/api/v1/certificados/emissao/{issuer_id}",
    "/api/v1/fiscal-monitor/status/{client_id}",
]

# Rotas que alteram ou acionam: A não pode receber 2xx.
ESCRITAS = [
    ("PATCH", "/api/v1/clients/{client_id}", {"name": "Invadido por A"}),
    ("PUT", "/api/v1/clients/{client_id}", {"name": "Invadido por A"}),
    ("DELETE", "/api/v1/clients/{client_id}", None),
    ("PATCH", "/api/v1/clients/{client_id}/billing-config", {"monthly_fee": 1}),
    ("POST", "/api/v1/clients/{client_id}/reminders", {"kind": "custom", "message": "oi"}),
    ("PUT", "/api/v1/obligations/profiles/{client_id}", {}),
    ("POST", "/api/v1/clients/{client_id}/partners",
     {"name": "Sócio de A", "cpf": "52998224725", "participation_percentage": "10"}),
    ("POST", "/api/v1/clients/{client_id}/company-documents",
     {"document_type": "cnpj", "file_url": "https://example.com/a.pdf"}),
    ("POST", "/api/v1/clients/{client_id}/ai-summary", None),
    ("POST", "/api/v1/fiscal-monitor/sync/{client_id}", None),
    ("POST", "/api/v1/ecac/fiscal-situation/{client_id}/refresh", None),
    ("PATCH", "/api/v1/deadlines/{deadline_id}", {"title": "Invadido por A"}),
    ("DELETE", "/api/v1/deadlines/{deadline_id}", None),
    ("PUT", "/api/v1/guias/{guia_id}", {"valor": 1}),
    ("PUT", "/api/v1/guias/{guia_id}/mark-paid", {}),
    ("PUT", "/api/v1/ecac/proxies/{proxy_id}", {"status": "revogada"}),
    ("PATCH", "/api/v1/obligations/instances/{instance_id}", {"notes": "Invadido por A"}),
    ("DELETE", "/api/v1/obligations/instances/{instance_id}", None),
    ("DELETE", "/api/v1/developer/api-keys/{key_id}", None),
    ("PUT", "/api/v1/developer/webhooks/{sub_id}", {"url": "https://atacante.example/x"}),
    ("POST", "/api/v1/developer/webhooks/{sub_id}/rotate-secret", None),
    ("DELETE", "/api/v1/developer/webhooks/{sub_id}", None),
    ("POST", "/api/v1/invoices/{invoice_id}/emit", None),
    ("POST", "/api/v1/invoices/{invoice_id}/cancel", {"reason": "Cancelamento indevido feito por A"}),
    ("PUT", "/api/v1/certificados/emissao/{issuer_id}", {"modo_certificado": "procuracao"}),
    ("POST", "/api/v1/certificados/emissao/{issuer_id}/testar", None),
    ("POST", "/api/v1/certificados/{cert_id}/bloquear", {"motivo": "Invadido por A"}),
    ("POST", "/api/v1/certificados/{cert_id}/desbloquear", None),
    ("DELETE", "/api/v1/certificados/{cert_id}", None),
]


async def test_escritorio_a_nao_alcanca_registros_de_b(
    client_with_auth_a, dono_b, client_b, tenant_b, test_db, chave_cofre
):
    http_a, user_a, _, _ = client_with_auth_a
    user_a.role = UserRole.OWNER  # o dono de A tem a permissão mais ampla
    await test_db.commit()
    ids = await _recursos_de_b(dono_b, client_b, test_db, tenant_b.id)

    for rota in LEITURAS:
        url = rota.format(**ids)
        assert dono_b.get(url).status_code == 200, f"controle: B não leu {url}"
        r = http_a.get(url)
        assert r.status_code in (403, 404), f"IDOR: A leu {url} de B ({r.status_code})"
        assert "Prazo de B" not in r.text and "Consultoria de B" not in r.text

    for metodo, rota, corpo in ESCRITAS:
        url = rota.format(**ids)
        r = http_a.request(metodo, url, json=corpo) if corpo is not None else http_a.request(metodo, url)
        assert r.status_code >= 400, f"IDOR: A executou {metodo} {url} em B ({r.status_code} {r.text})"
        # 422 = corpo inválido: o teste não chegou à checagem de escritório.
        assert r.status_code not in (422, 500), f"{metodo} {url}: {r.status_code} {r.text}"

    # Depois de todas as tentativas de A, os registros de B continuam intactos.
    assert dono_b.get(f"/api/v1/clients/{ids['client_id']}").json()["name"] == client_b.name
    assert dono_b.get(f"/api/v1/deadlines/{ids['deadline_id']}").json()["title"] == "Prazo de B"
    assert any(k["id"] == ids["key_id"] for k in dono_b.get("/api/v1/developer/api-keys").json())
    webhooks = dono_b.get("/api/v1/developer/webhooks").json()
    assert [w["url"] for w in webhooks if w["id"] == ids["sub_id"]] == ["https://example.com/webhook-b"]
    cert = (await test_db.execute(
        select(CertificadoA1).where(CertificadoA1.id == uuid.UUID(ids["cert_id"]))
    )).scalar_one()
    await test_db.refresh(cert)
    assert cert.status == "valido"


async def test_emissor_de_a_nao_usa_certificado_de_b(
    client_with_auth_a, dono_b, client_b, tenant_b, test_db, chave_cofre
):
    """Sem RLS, o PUT /certificados/emissao aceitava o certificado_id de outro
    escritório: o emissor de A passaria a emitir NFS-e com o certificado A1 de B."""
    http_a, user_a, client_a, _ = client_with_auth_a
    ids = await _recursos_de_b(dono_b, client_b, test_db, tenant_b.id)
    issuer_a = _ok(http_a.post("/api/v1/invoices/issuers", json={
        "client_id": str(client_a.id), "cnpj": client_a.document, "inscricao_municipal": "123456",
        "regime_tributario": "simples", "municipio_ibge": "3550308",
        "cod_servico_lc116": "17.01", "aliquota_iss": "0.02",
    }))["id"]

    r = http_a.put(f"/api/v1/certificados/emissao/{issuer_a}", json={
        "modo_certificado": "procuracao", "certificado_id": ids["cert_id"],
        "procuracao_confirmada": True,
    })
    assert r.status_code == 404, r.text
    assert http_a.get(f"/api/v1/certificados/emissao/{issuer_a}").json()["certificado_id"] is None

    with pytest.raises(cofre.CertificadoIndisponivel):
        await cofre.obter_material(
            test_db, uuid.UUID(ids["cert_id"]), tenant_id=user_a.tenant_id, finalidade="teste"
        )
