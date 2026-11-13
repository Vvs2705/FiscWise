"""Oferta de reconquista pós-teste grátis (decisão do dono, 13/11/2026).

- Sai 5 dias depois de o teste vencer, uma vez por escritório, só para quem
  nunca pagou e não se descadastrou; lembrete no 6º dia; vale 7 dias.
- Checkout com `oferta: true`: preço calculado no servidor (15% no 1º mês do
  mensal; anual com 25% no total) e a oferta vai no external_reference.
- Webhooks aceitam o valor promocional só com a oferta; a 1ª cobrança do
  mensal dispara o PUT para o preço cheio; anual promo ativa 12 meses.
- Descadastro por link com token assinado.
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy import select

from app.api.v1.endpoints import billing as billing_ep
from app.api.v1.endpoints.billing import montar_referencia
from app.core.config import settings
from app.core.pricing import preco_oferta
from app.core.security import get_password_hash
from app.models.billing import RetentionOffer, TenantSubscription
from app.models.tenant import SubscriptionStatus, Tenant
from app.models.user import User, UserRole
from app.services import email_service
from app.services import mercadopago as mp_module
from app.services.oferta import (
    STATUS_ACEITA,
    STATUS_ENVIADA,
    STATUS_OPTOUT,
    enviar_lembretes,
    enviar_ofertas_novas,
    montar_token_descadastro,
    reconciliar_reajustes,
)
from tests.test_plan_enforcement import authed_client, premium_setup, register_client  # noqa: F401

AGORA = datetime(2026, 11, 20, 13, 0, tzinfo=timezone.utc)  # 10h em Brasília


def _aware(dt):
    return dt.replace(tzinfo=timezone.utc) if dt is not None and dt.tzinfo is None else dt


class _Gateway:
    def __init__(self):
        self.assinaturas: list[dict] = []
        self.cobrancas: list[dict] = []
        self.reajustes: list[tuple] = []
        self.preapproval: dict = {}
        self.autorizado: dict = {}
        self.pagamento: dict = {}
        self.falhar_reajuste = False

    def configurado(self):
        return True

    async def criar_assinatura(self, **kw):
        self.assinaturas.append(kw)
        return {"tipo": "assinatura", "id": "pre_x", "init_point": "https://mp/pre"}

    async def criar_cobranca_unica(self, **kw):
        self.cobrancas.append(kw)
        return {"tipo": "cobranca_unica", "id": "pref_x", "init_point": "https://mp/pref"}

    async def atualizar_valor_assinatura(self, pre_id, valor):
        if self.falhar_reajuste:
            raise mp_module.GatewayPagamentoError("fora do ar", status_code=500)
        self.reajustes.append((pre_id, float(valor)))
        return {}

    async def cancelar_assinatura(self, pre_id):
        return {}

    async def obter_preapproval(self, _id):
        return self.preapproval

    async def obter_pagamento_autorizado(self, _id):
        return self.autorizado

    async def obter_pagamento(self, _id):
        return self.pagamento


@pytest.fixture
def gw(monkeypatch):
    g = _Gateway()
    monkeypatch.setattr(billing_ep, "gateway", g)
    monkeypatch.setattr(mp_module, "gateway", g)
    monkeypatch.setattr(settings, "MERCADO_PAGO_WEBHOOK_SECRET", "", raising=False)
    monkeypatch.setattr(settings, "PAGAMENTOS_GO_LIVE", True, raising=False)
    return g


@pytest.fixture
def enviados(monkeypatch):
    lista = []

    async def fake_send(to, subject, html, idempotency_key=None):
        lista.append((to, subject, html))
        return True

    monkeypatch.setattr(email_service, "send_email", fake_send)
    return lista


def _sub(plan, tenant_id, *, vencido_ha_dias: float, status="trialing") -> TenantSubscription:
    return TenantSubscription(
        tenant_id=tenant_id, plan_id=plan.id, status=status,
        trial_ends_at=AGORA - timedelta(days=vencido_ha_dias),
        billing_cycle="mensal", amount=plan.price_monthly, billing_provider="mercadopago",
    )


async def _escritorio(test_db, plan, *, vencido_ha_dias, status="trialing", opt_out=False):
    tenant = Tenant(
        id=uuid.uuid4(), name=f"Escritório {uuid.uuid4().hex[:6]}",
        subscription_status=SubscriptionStatus.TRIAL, plan_slug="premium",
        terms_accepted_at=AGORA,
    )
    test_db.add(tenant)
    await test_db.flush()
    dono = User(
        id=uuid.uuid4(), tenant_id=tenant.id, email=f"{uuid.uuid4().hex[:8]}@teste.com",
        hashed_password=get_password_hash("Password123!"), role=UserRole.OWNER, is_active=True,
        marketing_opt_out_at=AGORA if opt_out else None,
    )
    test_db.add(dono)
    test_db.add(_sub(plan, tenant.id, vencido_ha_dias=vencido_ha_dias, status=status))
    await test_db.commit()
    return tenant, dono


async def _oferta(test_db, tenant_id, *, enviada_ha_dias=1.0, expira_em_dias=6.0) -> RetentionOffer:
    oferta = RetentionOffer(
        tenant_id=tenant_id, status=STATUS_ENVIADA,
        sent_at=datetime.now(timezone.utc) - timedelta(days=enviada_ha_dias),
        expires_at=datetime.now(timezone.utc) + timedelta(days=expira_em_dias),
    )
    test_db.add(oferta)
    await test_db.commit()
    return oferta


# ── Envio e lembrete ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_so_elegiveis_recebem_e_uma_vez(test_db, premium_setup, enviados):  # noqa: F811
    plan, tenant, user = premium_setup
    test_db.add(_sub(plan, tenant.id, vencido_ha_dias=6))
    await test_db.commit()
    await _escritorio(test_db, plan, vencido_ha_dias=4)                    # cedo demais
    await _escritorio(test_db, plan, vencido_ha_dias=6, status="active")   # pagou
    _, descadastrado = await _escritorio(test_db, plan, vencido_ha_dias=6, opt_out=True)

    r = await enviar_ofertas_novas(test_db, AGORA)
    assert r["sent"] == 1 and r["optout"] == 1
    assert [e[0] for e in enviados] == [user.email]
    assunto, html = enviados[0][1], enviados[0][2]
    assert assunto == "Uma oferta para você voltar ao FiscWise"
    o = preco_oferta(plan.price_monthly)
    assert "254,15" in html and "2.691,00" in html  # 15% no 1º mês e anual 25%
    assert "Não quero mais receber ofertas" in html and "/api/v1/marketing/descadastro?token=" in html

    oferta = (await test_db.execute(
        select(RetentionOffer).where(RetentionOffer.tenant_id == tenant.id)
    )).scalar_one()
    assert oferta.status == STATUS_ENVIADA
    assert _aware(oferta.expires_at) == AGORA + timedelta(days=7)
    assert o["mensal_promo"] == 254.15

    # Rodar de novo não manda outra.
    r2 = await enviar_ofertas_novas(test_db, AGORA + timedelta(hours=1))
    assert r2["sent"] == 0
    optout = (await test_db.execute(
        select(RetentionOffer).where(RetentionOffer.tenant_id == descadastrado.tenant_id)
    )).scalar_one()
    assert optout.status == STATUS_OPTOUT


@pytest.mark.asyncio
async def test_sem_resend_desfaz_e_tenta_de_novo(test_db, premium_setup, monkeypatch):  # noqa: F811
    plan, tenant, _ = premium_setup
    test_db.add(_sub(plan, tenant.id, vencido_ha_dias=6))
    await test_db.commit()

    async def falha(**_kw):
        return False

    monkeypatch.setattr(email_service, "send_email", falha)
    r = await enviar_ofertas_novas(test_db, AGORA)
    assert r["failed"] == 1
    assert (await test_db.execute(select(RetentionOffer))).scalars().all() == []


@pytest.mark.asyncio
async def test_lembrete_no_sexto_dia_uma_vez(test_db, premium_setup, enviados):  # noqa: F811
    plan, tenant, user = premium_setup
    oferta = RetentionOffer(
        tenant_id=tenant.id, status=STATUS_ENVIADA,
        sent_at=AGORA - timedelta(days=5), expires_at=AGORA + timedelta(days=2),
    )
    test_db.add(oferta)
    await test_db.commit()

    assert (await enviar_lembretes(test_db, AGORA))["sent"] == 0       # 5º dia
    r = await enviar_lembretes(test_db, AGORA + timedelta(days=1))     # 6º dia
    assert r["sent"] == 1
    assert enviados[-1][1].startswith("Última chance")
    assert (await enviar_lembretes(test_db, AGORA + timedelta(days=1, hours=1)))["sent"] == 0


# ── Checkout ─────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_checkout_com_oferta_calcula_no_servidor(test_db, premium_setup, authed_client, gw):  # noqa: F811
    plan, tenant, user = premium_setup
    test_db.add(_sub(plan, tenant.id, vencido_ha_dias=6))
    await test_db.commit()
    oferta = await _oferta(test_db, tenant.id)
    client = authed_client(user)
    o = preco_oferta(plan.price_monthly)

    info = client.get("/api/v1/billing/oferta").json()
    assert info["ativa"] is True
    assert info["planos"][0]["mensal_promo"] == o["mensal_promo"]

    r = client.post("/api/v1/billing/checkout", json={
        "plan_slug": "premium", "ciclo": "mensal", "metodo": "cartao", "oferta": True,
        "valor": 1,  # ignorado: o preço nunca vem do cliente
    })
    assert r.status_code == 201, r.text
    chamada = gw.assinaturas[-1]
    assert chamada["preco_mensal"] == o["mensal_promo"]
    assert "1º mês" in chamada["reason"]
    assert chamada["referencia"].endswith(f"|premium|mensal|{oferta.id}")

    r = client.post("/api/v1/billing/checkout", json={
        "plan_slug": "premium", "ciclo": "anual", "metodo": "pix", "oferta": True,
    })
    assert r.status_code == 201, r.text
    chamada = gw.cobrancas[-1]
    assert chamada["valor_oferta"] == o["anual_promo"]
    assert chamada["max_parcelas_oferta"] == 6
    assert chamada["expira_em"] is not None

    r = client.post("/api/v1/billing/checkout", json={
        "plan_slug": "premium", "ciclo": "trimestral", "metodo": "pix", "oferta": True,
    })
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_checkout_sem_oferta_ou_expirada_recusa(test_db, premium_setup, authed_client, gw):  # noqa: F811
    plan, tenant, user = premium_setup
    test_db.add(_sub(plan, tenant.id, vencido_ha_dias=6))
    await test_db.commit()
    client = authed_client(user)

    corpo = {"plan_slug": "premium", "ciclo": "mensal", "metodo": "cartao", "oferta": True}
    r = client.post("/api/v1/billing/checkout", json=corpo)
    assert r.status_code == 400
    assert r.headers.get("X-Error-Code") == "OFERTA_INDISPONIVEL"

    await _oferta(test_db, tenant.id, enviada_ha_dias=8, expira_em_dias=-1)
    r = client.post("/api/v1/billing/checkout", json=corpo)
    assert r.status_code == 400
    assert client.get("/api/v1/billing/oferta").json()["ativa"] is False


# ── Webhooks ─────────────────────────────────────────────────────────────────

async def _sub_em_teste(test_db, plan, tenant):
    sub = _sub(plan, tenant.id, vencido_ha_dias=6)
    test_db.add(sub)
    await test_db.commit()
    return sub


@pytest.mark.asyncio
async def test_preapproval_promo_so_com_oferta(test_db, premium_setup, register_client, gw):  # noqa: F811
    plan, tenant, _ = premium_setup
    sub = await _sub_em_teste(test_db, plan, tenant)
    oferta = await _oferta(test_db, tenant.id)
    promo = preco_oferta(plan.price_monthly)["mensal_promo"]

    # Sem a oferta na referência: valor promo recusado.
    gw.preapproval = {
        "status": "authorized", "auto_recurring": {"transaction_amount": promo},
        "external_reference": montar_referencia(sub.id, "premium", "mensal"),
    }
    r = register_client.post("/api/v1/billing/webhook/mercadopago?data.id=pre_1&type=subscription_preapproval",
                             json={"id": "n1", "type": "subscription_preapproval", "data": {"id": "pre_1"}})
    assert r.status_code == 200
    await test_db.refresh(sub)
    assert sub.status == "trialing"

    # Com a oferta: ativa e marca a oferta como aceita.
    gw.preapproval["external_reference"] = montar_referencia(sub.id, "premium", "mensal", oferta.id)
    r = register_client.post("/api/v1/billing/webhook/mercadopago?data.id=pre_1&type=subscription_preapproval",
                             json={"id": "n2", "type": "subscription_preapproval", "data": {"id": "pre_1"}})
    assert r.status_code == 200, r.text
    await test_db.refresh(sub)
    await test_db.refresh(oferta)
    assert sub.status == "active"
    assert sub.provider_subscription_id == "pre_1"
    assert sub.amount == plan.price_monthly  # sub guarda o preço cheio
    assert oferta.status == STATUS_ACEITA and oferta.preapproval_id == "pre_1"
    assert float(oferta.promo_amount) == promo and float(oferta.full_amount) == float(plan.price_monthly)


@pytest.mark.asyncio
async def test_cobranca_promo_reajusta_para_preco_cheio(test_db, premium_setup, register_client, gw):  # noqa: F811
    plan, tenant, _ = premium_setup
    sub = await _sub_em_teste(test_db, plan, tenant)
    sub.status = "active"
    sub.provider_subscription_id = "pre_2"
    sub.current_period_end = datetime.now(timezone.utc) + timedelta(days=30)
    oferta = await _oferta(test_db, tenant.id)
    promo = preco_oferta(plan.price_monthly)["mensal_promo"]
    oferta.status = STATUS_ACEITA
    oferta.accepted_at = datetime.now(timezone.utc)
    oferta.accepted_cycle = "mensal"
    oferta.preapproval_id = "pre_2"
    oferta.promo_amount = Decimal(str(promo))
    oferta.full_amount = plan.price_monthly
    await test_db.commit()

    gw.autorizado = {"preapproval_id": "pre_2", "transaction_amount": promo, "payment": {"status": "approved"}}
    r = register_client.post("/api/v1/billing/webhook/mercadopago?data.id=7001&type=subscription_authorized_payment",
                             json={"id": "c1", "type": "subscription_authorized_payment", "data": {"id": "7001"}})
    assert r.status_code == 200, r.text
    assert gw.reajustes == [("pre_2", float(plan.price_monthly))]
    await test_db.refresh(oferta)
    assert oferta.promo_charged_at is not None and oferta.price_bumped_at is not None

    # PUT não pegou: 2ª cobrança ainda promo → aceita (o cliente pagou) e reajusta de novo.
    r = register_client.post("/api/v1/billing/webhook/mercadopago?data.id=7002&type=subscription_authorized_payment",
                             json={"id": "c2", "type": "subscription_authorized_payment", "data": {"id": "7002"}})
    assert r.status_code == 200, r.text
    assert len(gw.reajustes) == 2
    await test_db.refresh(sub)
    assert sub.status == "active"


@pytest.mark.asyncio
async def test_reconciliacao_reajusta_quando_o_put_falhou(test_db, premium_setup, gw):  # noqa: F811
    plan, tenant, _ = premium_setup
    oferta = RetentionOffer(
        tenant_id=tenant.id, status=STATUS_ACEITA, accepted_at=AGORA, accepted_cycle="mensal",
        preapproval_id="pre_3", promo_amount=Decimal("254.15"), full_amount=plan.price_monthly,
    )
    test_db.add(oferta)
    await test_db.commit()

    gw.preapproval = {"summarized": {"charged_quantity": 0}}
    assert (await reconciliar_reajustes(test_db, AGORA))["pending"] == 1
    assert gw.reajustes == []

    gw.preapproval = {"summarized": {"charged_quantity": 1}}
    gw.falhar_reajuste = True
    assert (await reconciliar_reajustes(test_db, AGORA))["failed"] == 1

    gw.falhar_reajuste = False
    assert (await reconciliar_reajustes(test_db, AGORA))["bumped"] == 1
    assert gw.reajustes == [("pre_3", float(plan.price_monthly))]


@pytest.mark.asyncio
async def test_anual_promo_ativa_doze_meses(test_db, premium_setup, register_client, gw):  # noqa: F811
    plan, tenant, _ = premium_setup
    sub = await _sub_em_teste(test_db, plan, tenant)
    oferta = await _oferta(test_db, tenant.id)
    promo = preco_oferta(plan.price_monthly)["anual_promo"]
    gw.pagamento = {
        "status": "approved", "transaction_amount": promo,
        "external_reference": montar_referencia(sub.id, "premium", "anual", oferta.id),
    }
    r = register_client.post("/api/v1/billing/webhook/mercadopago?data.id=900&type=payment",
                             json={"id": "p1", "type": "payment", "data": {"id": "900"}})
    assert r.status_code == 200, r.text
    await test_db.refresh(sub)
    await test_db.refresh(oferta)
    assert sub.status == "active" and sub.billing_cycle == "anual"
    assert _aware(sub.current_period_end) > datetime.now(timezone.utc) + timedelta(days=359)
    assert oferta.status == STATUS_ACEITA and oferta.accepted_cycle == "anual"

    # Sem oferta na referência, o mesmo valor não ativa.
    sub2_tenant, _ = await _escritorio(test_db, plan, vencido_ha_dias=6)
    sub2 = (await test_db.execute(
        select(TenantSubscription).where(TenantSubscription.tenant_id == sub2_tenant.id)
    )).scalar_one()
    gw.pagamento = {
        "status": "approved", "transaction_amount": promo,
        "external_reference": montar_referencia(sub2.id, "premium", "anual"),
    }
    r = register_client.post("/api/v1/billing/webhook/mercadopago?data.id=901&type=payment",
                             json={"id": "p2", "type": "payment", "data": {"id": "901"}})
    assert r.status_code == 200
    await test_db.refresh(sub2)
    assert sub2.status == "trialing"


# ── Descadastro ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_descadastro_por_token(test_db, premium_setup, register_client):  # noqa: F811
    _, _, user = premium_setup
    r = register_client.get(f"/api/v1/marketing/descadastro?token={montar_token_descadastro(user.id)}")
    assert r.status_code == 200
    assert "não vai mais receber ofertas" in r.text
    await test_db.refresh(user)
    assert user.marketing_opt_out_at is not None

    r = register_client.get("/api/v1/marketing/descadastro?token=token-invalido-qualquer")
    assert r.status_code == 400
    assert "Link inválido" in r.text
