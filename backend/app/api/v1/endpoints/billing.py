"""Billing endpoints for FiscWise

Handles payment gateway webhooks and subscription management.
Supports Asaas (primary) with Iugu stub for future.
"""

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_current_user, get_db
from app.models.billing import BillingWebhookEvent, TenantSubscription
from app.models.plan import Plan
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User
from app.core.pricing import CICLOS_VALIDOS, get_ciclo, valores_aceitos
from app.services.mercadopago import (
    GatewayNaoConfiguradoError,
    GatewayPagamentoError,
    gateway,
    valor_centavos,
    validar_assinatura_webhook,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/billing", tags=["Billing"])

# Campos que denunciam dados de cartão chegando ao servidor (Checkout Pro NÃO
# deve receber PAN/CVV — o cliente paga no ambiente hospedado do Mercado Pago).
_CAMPOS_CARTAO = {
    "card_number", "cardnumber", "numero_cartao", "cvv", "cvc", "security_code",
    "card_cvv", "expiration", "card", "cartao",
}


# ─── Schemas ──────────────────────────────────────────────────────────────────

class SubscriptionOut(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    plan_id: uuid.UUID
    billing_provider: Optional[str]
    status: str
    current_period_end: Optional[str]
    trial_ends_at: Optional[str]
    amount: Optional[str]
    currency: str
    created_at: str


class CreateSubscriptionRequest(BaseModel):
    plan_id: uuid.UUID
    billing_provider: Optional[str] = None  # 'asaas' | 'iugu' | 'manual'


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _fmt(dt: Optional[datetime]) -> Optional[str]:
    return dt.isoformat() if dt else None


async def _refletir_plano_no_tenant(db: AsyncSession, sub: TenantSubscription) -> None:
    """Ativação paga confirmada → tenant.plan_slug = slug do plano da assinatura.

    O paywall lê tenants.plan_slug (plan_access); sem isso o cliente paga e
    continua no plano antigo. Suspensão NÃO mexe no tenant: o enforcement em
    plan_access.effective_plan_slug já degrada para free.
    """
    plan_slug = (
        await db.execute(select(Plan.slug).where(Plan.id == sub.plan_id))
    ).scalar_one_or_none()
    if not plan_slug:
        return
    tenant = (
        await db.execute(select(Tenant).where(Tenant.id == sub.tenant_id))
    ).scalar_one_or_none()
    if tenant is not None:
        tenant.plan_slug = plan_slug
        tenant.subscription_status = SubscriptionStatus.ACTIVE


def _sub_out(sub: TenantSubscription) -> SubscriptionOut:
    return SubscriptionOut(
        id=sub.id,
        tenant_id=sub.tenant_id,
        plan_id=sub.plan_id,
        billing_provider=sub.billing_provider,
        status=sub.status,
        current_period_end=_fmt(sub.current_period_end),
        trial_ends_at=_fmt(sub.trial_ends_at),
        amount=str(sub.amount) if sub.amount else None,
        currency=sub.currency,
        created_at=sub.created_at.isoformat(),
    )


# ─── Subscription endpoints ───────────────────────────────────────────────────

@router.get("/subscription", response_model=SubscriptionOut)
async def get_my_subscription(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    """Get the current tenant's subscription details."""
    result = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == current_user.tenant_id
        )
    )
    sub = result.scalar_one_or_none()
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nenhuma assinatura encontrada para este tenant",
        )
    return _sub_out(sub)


@router.post("/subscription", response_model=SubscriptionOut, status_code=status.HTTP_201_CREATED)
async def create_or_update_subscription(
    body: CreateSubscriptionRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    """
    Create or update the billing subscription for this tenant.

    Owner only. In production, this also calls the billing provider API.
    """
    if current_user.role.value != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário pode gerenciar assinaturas",
        )

    plan_result = await db.execute(select(Plan).where(Plan.id == body.plan_id))
    plan = plan_result.scalar_one_or_none()
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plano não encontrado")

    existing_result = await db.execute(
        select(TenantSubscription).where(
            TenantSubscription.tenant_id == current_user.tenant_id
        )
    )
    sub = existing_result.scalar_one_or_none()

    if sub:
        sub.plan_id = body.plan_id
        if body.billing_provider:
            sub.billing_provider = body.billing_provider
        sub.amount = plan.price_monthly
    else:
        sub = TenantSubscription(
            tenant_id=current_user.tenant_id,
            plan_id=body.plan_id,
            billing_provider=body.billing_provider,
            status="trialing",
            amount=plan.price_monthly,
            currency="BRL",
        )
        db.add(sub)

    await db.commit()
    await db.refresh(sub)
    logger.info("Subscription upserted: tenant=%s plan=%s", current_user.tenant_id, plan.slug)
    return _sub_out(sub)


# ─── Webhook endpoints ────────────────────────────────────────────────────────

@router.post("/webhooks/asaas", status_code=status.HTTP_200_OK)
async def asaas_webhook(
    request: Request,
    asaas_access_token: Optional[str] = Header(default=None, alias="asaas-access-token"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Receive Asaas webhook events (public — no JWT).

    Idempotent: duplicate events return 200 silently.
    Configure BILLING_WEBHOOK_SECRET for signature verification.
    """
    from app.services.billing_service import (
        verify_asaas_signature,
        record_webhook_event,
        mark_event_processed,
        dispatch_asaas_event,
    )

    raw_body = await request.body()

    if not verify_asaas_signature(raw_body, asaas_access_token or ""):
        logger.warning("Asaas webhook signature mismatch")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON")

    event_type = payload.get("event", "UNKNOWN")
    payment = payload.get("payment", {})
    event_id = payment.get("id") or str(uuid.uuid4())

    event = await record_webhook_event(db, "asaas", event_id, event_type, payload)
    if event is None:
        return {"status": "already_processed"}

    try:
        result = await dispatch_asaas_event(db, event_type, payload)
        await mark_event_processed(db, event)
    except Exception as exc:
        await mark_event_processed(db, event, error=str(exc))
        logger.error("Asaas event %s error: %s", event_id, exc, exc_info=True)
        return {"status": "error_logged"}

    return {"status": result, "event_type": event_type}


# ─── Mercado Pago: config + checkout + webhook ────────────────────────────────

class CheckoutRequest(BaseModel):
    plan_slug: str
    ciclo: str = "mensal"          # mensal | trimestral | semestral | anual
    metodo: str = "cartao"         # pix | cartao (ignorado no mensal, que é recorrente no cartão)


class CheckoutResponse(BaseModel):
    tipo: str
    id: Optional[str]
    init_point: Optional[str]


class PagamentoConfigResponse(BaseModel):
    gateway: str = "mercadopago"
    public_key: str
    go_live: bool


@router.get("/config", response_model=PagamentoConfigResponse)
async def billing_config(current_user: User = Depends(get_current_user)) -> PagamentoConfigResponse:
    """Dados públicos do gateway para o frontend (public key é seguro expor)."""
    return PagamentoConfigResponse(
        public_key=settings.MERCADO_PAGO_PUBLIC_KEY,
        go_live=settings.PAGAMENTOS_GO_LIVE,
    )


@router.post("/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
async def criar_checkout(
    body: CheckoutRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CheckoutResponse:
    """Cria a assinatura mensal (preapproval) no Mercado Pago e devolve o init_point.

    Owner only · rejeita dados de cartão (sempre 400) · 503 enquanto
    PAGAMENTOS_GO_LIVE desligado · valor calculado no servidor a partir do Plan.
    """
    # Rejeita PAN/CVV ANTES do gate de go-live (sempre 400).
    try:
        raw = await request.json()
    except Exception:
        raw = {}
    if isinstance(raw, dict) and any(str(k).lower() in _CAMPOS_CARTAO for k in raw):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dados de cartão não são aceitos aqui (use o checkout do Mercado Pago).",
        )

    if current_user.role.value != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário pode assinar",
        )
    if not settings.PAGAMENTOS_GO_LIVE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Pagamentos em configuração — cobrança ainda não habilitada.",
        )

    if body.ciclo not in CICLOS_VALIDOS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Ciclo inválido: {body.ciclo}")
    if body.metodo not in ("pix", "cartao"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Método inválido: {body.metodo}")

    plan = (
        await db.execute(select(Plan).where(Plan.slug == body.plan_slug))
    ).scalar_one_or_none()
    if not plan or plan.price_monthly is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Plano inválido")

    sub = (
        await db.execute(
            select(TenantSubscription).where(
                TenantSubscription.tenant_id == current_user.tenant_id
            )
        )
    ).scalar_one_or_none()
    if sub is None:
        sub = TenantSubscription(
            tenant_id=current_user.tenant_id, plan_id=plan.id,
            status="trialing", currency="BRL",
        )
        db.add(sub)
        await db.flush()
    sub.plan_id = plan.id
    sub.billing_provider = "mercadopago"
    sub.amount = plan.price_monthly
    sub.billing_cycle = body.ciclo

    try:
        if body.ciclo == "mensal":
            # Assinatura recorrente no cartão (preapproval).
            resultado = await gateway.criar_assinatura(
                plano_nome=plan.name, preco_mensal=plan.price_monthly,
                email_pagador=current_user.email, referencia=str(sub.id),
            )
        else:
            # Ciclo pré-pago: checkout único (Pix -15% ou cartão até 6x sem juros).
            resultado = await gateway.criar_cobranca_unica(
                plano_nome=plan.name, preco_mensal=plan.price_monthly,
                ciclo=body.ciclo, metodo=body.metodo,
                email_pagador=current_user.email, referencia=str(sub.id),
            )
    except GatewayNaoConfiguradoError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except GatewayPagamentoError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

    if resultado.get("id") and resultado.get("tipo") == "assinatura":
        # Só o preapproval é uma assinatura no gateway; cobranças únicas se
        # correlacionam pelo external_reference (= sub.id) no webhook `payment`.
        sub.provider_subscription_id = str(resultado["id"])
    await db.commit()
    logger.info(
        "Checkout MP criado: tenant=%s plano=%s ciclo=%s metodo=%s",
        current_user.tenant_id, plan.slug, body.ciclo, body.metodo,
    )
    return CheckoutResponse(**resultado)


@router.post("/webhook/mercadopago", status_code=status.HTTP_200_OK)
async def mercadopago_webhook(
    request: Request,
    x_signature: Optional[str] = Header(default=None, alias="x-signature"),
    x_request_id: Optional[str] = Header(default=None, alias="x-request-id"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Webhook do Mercado Pago — HMAC-validado, idempotente, reconcilia no gateway.

    NUNCA confia no corpo: consulta o gateway, casa pela assinatura local
    (provider_subscription_id) e só ativa se autorizado E valor conferido.
    Cancelamento/pausa do preapproval → suspende o acesso (proteção de receita).
    """
    try:
        body = await request.json()
    except Exception:
        body = {}

    tipo = (body.get("type") or body.get("topic") or "").lower()
    data = body.get("data") or {}
    recurso_id = str(
        data.get("id") or body.get("id") or request.query_params.get("data.id") or ""
    )

    if not validar_assinatura_webhook(
        x_signature=x_signature, x_request_id=x_request_id,
        data_id=recurso_id, max_idade_segundos=600,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Assinatura inválida")

    if not recurso_id:
        return {"status": "ignorado"}

    # Idempotência: dedup pela notificação (id do corpo, senão x-request-id).
    event_id = str(body.get("id") or x_request_id or f"{tipo}:{recurso_id}")
    evento = BillingWebhookEvent(
        provider="mercadopago", event_id=event_id,
        event_type=tipo or "desconhecido", payload=body,
    )
    db.add(evento)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        return {"status": "already_processed"}

    if gateway.configurado() and tipo in ("preapproval", "subscription_preapproval"):
        try:
            pre = await gateway.obter_preapproval(recurso_id)
            pre_status = (pre.get("status") or "").lower()
            valor_mensal = int(
                round(float((pre.get("auto_recurring") or {}).get("transaction_amount") or 0) * 100)
            )
            sub = (
                await db.execute(
                    select(TenantSubscription).where(
                        TenantSubscription.provider_subscription_id == recurso_id
                    )
                )
            ).scalar_one_or_none()
            if sub is not None:
                agora = datetime.now(timezone.utc)
                sub.last_event_id = event_id
                sub.last_event_at = agora
                if pre_status == "authorized":
                    if valor_mensal and sub.amount is not None and valor_mensal != valor_centavos(sub.amount):
                        logger.warning(
                            "webhook_valor_divergente sub=%s esperado=%s pago=%s",
                            sub.id, valor_centavos(sub.amount), valor_mensal,
                        )
                    else:
                        sub.status = "active"
                        sub.current_period_start = agora
                        sub.current_period_end = agora + timedelta(days=30)
                        await _refletir_plano_no_tenant(db, sub)
                elif pre_status in ("cancelled", "paused"):
                    if sub.status in ("active", "trialing", "past_due"):
                        sub.status = "suspended"
                        if pre_status == "cancelled":
                            sub.cancelled_at = agora
            evento.processed = True
            evento.processed_at = datetime.now(timezone.utc)
        except GatewayPagamentoError as exc:
            logger.warning("webhook_reconciliacao_falhou: %s", exc)

    elif gateway.configurado() and tipo == "payment":
        # Ciclos pré-pagos (trimestral/semestral/anual): pagamento único.
        # Reconcilia no gateway; casa pelo external_reference (= sub.id) e só
        # ativa se aprovado E valor == Pix ou cartão esperado para o ciclo.
        try:
            pag = await gateway.obter_pagamento(recurso_id)
            pag_status = (pag.get("status") or "").lower()
            external_ref = str(pag.get("external_reference") or "")
            try:
                sub_id = uuid.UUID(external_ref)
            except ValueError:
                sub_id = None
            sub = None
            if sub_id is not None:
                sub = (
                    await db.execute(
                        select(TenantSubscription).where(TenantSubscription.id == sub_id)
                    )
                ).scalar_one_or_none()
            if sub is not None:
                agora = datetime.now(timezone.utc)
                sub.last_event_id = event_id
                sub.last_event_at = agora
                pago_cent = int(round(float(pag.get("transaction_amount") or 0) * 100))
                aceitos_cent = {
                    int(round(v * 100))
                    for v in valores_aceitos(sub.amount or 0, sub.billing_cycle)
                }
                if pag_status == "approved":
                    if pago_cent not in aceitos_cent:
                        # Valor divergente → NÃO ativa (revisão manual via evento).
                        logger.warning(
                            "webhook_valor_divergente sub=%s ciclo=%s aceitos=%s pago=%s",
                            sub.id, sub.billing_cycle, aceitos_cent, pago_cent,
                        )
                    else:
                        ciclo_info = get_ciclo(sub.billing_cycle) or {"meses": 1}
                        sub.status = "active"
                        sub.current_period_start = agora
                        sub.current_period_end = agora + timedelta(days=30 * int(ciclo_info["meses"]))
                        await _refletir_plano_no_tenant(db, sub)
                elif pag_status in ("refunded", "charged_back"):
                    # Estorno/chargeback → suspende (proteção de receita).
                    if sub.status in ("active", "trialing", "past_due"):
                        sub.status = "suspended"
            evento.processed = True
            evento.processed_at = datetime.now(timezone.utc)
        except GatewayPagamentoError as exc:
            logger.warning("webhook_reconciliacao_falhou: %s", exc)

    await db.commit()
    return {"status": "ok"}
