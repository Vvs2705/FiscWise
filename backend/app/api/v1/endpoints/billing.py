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
    billing_cycle: str = "mensal"
    # Preenchido quando o dono pediu o cancelamento: o acesso pago continua
    # até current_period_end e não há nova cobrança.
    cancelled_at: Optional[str] = None


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
        billing_cycle=sub.billing_cycle or "mensal",
        cancelled_at=_fmt(sub.cancelled_at),
    )


def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:  # SQLite devolve datetimes naive
        return dt.replace(tzinfo=timezone.utc)
    return dt


def montar_referencia(sub_id: uuid.UUID, plan_slug: str, ciclo: str) -> str:
    """external_reference do checkout: `<id da assinatura>|<plano>|<ciclo>`."""
    return f"{sub_id}|{plan_slug}|{ciclo}"


def ler_referencia(ref: object) -> tuple[Optional[uuid.UUID], Optional[str], Optional[str]]:
    """Lê o external_reference. Aceita o formato antigo (só o id da assinatura)."""
    partes = str(ref or "").split("|")
    try:
        sub_id = uuid.UUID(partes[0])
    except ValueError:
        return None, None, None
    plan_slug = partes[1] if len(partes) > 1 and partes[1] else None
    ciclo = partes[2] if len(partes) > 2 and partes[2] in CICLOS_VALIDOS else None
    return sub_id, plan_slug, ciclo


async def _plano_por_slug(db: AsyncSession, slug: Optional[str]) -> Optional[Plan]:
    if not slug:
        return None
    return (await db.execute(select(Plan).where(Plan.slug == slug))).scalar_one_or_none()


async def _aplicar_uma_vez(db: AsyncSession, chave: str) -> bool:
    """True só na 1ª vez que `chave` aparece (trava no índice único dos eventos).

    O MP manda o mesmo pagamento em dois formatos (`?data.id=&type=` e
    `?id=&topic=`), com ids de notificação diferentes e às vezes no mesmo
    milissegundo. A trava é por recurso + status, então "aprovado" conta uma
    vez e um estorno posterior (outro status) ainda é processado.
    """
    try:
        async with db.begin_nested():
            db.add(BillingWebhookEvent(
                provider="mercadopago", event_id=chave, event_type="aplicado",
                payload={}, processed=True, processed_at=datetime.now(timezone.utc),
            ))
        return True
    except IntegrityError:
        return False


async def _cancelar_recorrencia_antiga(sub: TenantSubscription, nova_id: Optional[str]) -> None:
    """Troca de plano/ciclo pago: para a cobrança do preapproval anterior.

    Sem isso o cliente que passa do mensal para o trimestral (ou troca de
    plano no mensal) continuaria pagando as duas coisas.
    """
    antiga = sub.provider_subscription_id
    if not antiga or antiga == nova_id:
        return
    try:
        await gateway.cancelar_assinatura(antiga)
        logger.info("Recorrência antiga cancelada na troca: sub=%s pre=%s", sub.id, antiga)
    except GatewayPagamentoError as exc:
        # Não trava a ativação do que já foi pago; fica no log para cancelar à mão.
        logger.error("cancelar_recorrencia_antiga_falhou sub=%s pre=%s: %s", sub.id, antiga, exc)


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


@router.post("/subscription/cancel", response_model=SubscriptionOut)
async def cancelar_assinatura(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SubscriptionOut:
    """Cancela a assinatura em um clique (Termos, seção 4: sem multa).

    - Para a cobrança: no mensal, cancela o preapproval no Mercado Pago.
    - Período já pago: o acesso continua até current_period_end e depois o
      plano volta para o Gratuito (plan_access.effective_plan_slug).
    - Sem período pago (teste/checkout não concluído): encerra na hora.
    Idempotente: cancelar de novo devolve o mesmo estado.
    """
    if current_user.role.value != "owner":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas o proprietário do escritório pode cancelar a assinatura",
        )
    sub = (
        await db.execute(
            select(TenantSubscription).where(
                TenantSubscription.tenant_id == current_user.tenant_id
            )
        )
    ).scalar_one_or_none()
    if sub is None or sub.status in ("cancelled", "suspended"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não há assinatura ativa para cancelar.",
        )
    if sub.cancelled_at is not None:
        return _sub_out(sub)

    # Para a cobrança recorrente ANTES de gravar: se o gateway falhar, nada muda
    # aqui e o cliente pode tentar de novo (nunca "cancelado" com cartão cobrando).
    if sub.provider_subscription_id and sub.billing_provider == "mercadopago":
        try:
            await gateway.cancelar_assinatura(sub.provider_subscription_id)
        except GatewayNaoConfiguradoError as exc:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
        except GatewayPagamentoError as exc:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Não foi possível cancelar no Mercado Pago agora. Tente de novo em instantes.",
            ) from exc

    agora = datetime.now(timezone.utc)
    sub.cancelled_at = agora
    fim = _aware(sub.current_period_end)
    if sub.status != "active" or fim is None or fim <= agora:
        # Nada pago em vigor: encerra já.
        sub.status = "cancelled"
        tenant = (
            await db.execute(select(Tenant).where(Tenant.id == sub.tenant_id))
        ).scalar_one_or_none()
        if tenant is not None:
            tenant.subscription_status = SubscriptionStatus.CANCELLED
    await db.commit()
    await db.refresh(sub)
    logger.info("Assinatura cancelada pelo dono: tenant=%s ate=%s", sub.tenant_id, fim)
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
            status="trialing", currency="BRL", billing_provider="mercadopago",
            amount=plan.price_monthly, billing_cycle=body.ciclo,
        )
        db.add(sub)
        await db.flush()
    # A linha da assinatura guarda o que está PAGO. Abrir um checkout não muda
    # plano, ciclo, valor nem o id da recorrência: o pedido viaja no
    # external_reference e só vale quando o webhook confirmar o pagamento.
    # (Antes, abrir o mensal e depois o trimestral deixava ciclo=trimestral com
    # o id do preapproval antigo, mesmo sem pagar nada.)
    referencia = montar_referencia(sub.id, plan.slug, body.ciclo)

    try:
        if body.ciclo == "mensal":
            # Assinatura recorrente no cartão (preapproval).
            resultado = await gateway.criar_assinatura(
                plano_nome=plan.name, preco_mensal=plan.price_monthly,
                email_pagador=current_user.email, referencia=referencia,
            )
        else:
            # Ciclo pré-pago: checkout único (Pix -15% ou cartão até 6x sem juros).
            resultado = await gateway.criar_cobranca_unica(
                plano_nome=plan.name, preco_mensal=plan.price_monthly,
                ciclo=body.ciclo, metodo=body.metodo,
                email_pagador=current_user.email, referencia=referencia,
            )
    except GatewayNaoConfiguradoError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except GatewayPagamentoError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)) from exc

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
    if not isinstance(body, dict):
        body = {}

    qp = request.query_params
    tipo = (body.get("type") or body.get("topic") or qp.get("type") or qp.get("topic") or "").lower()
    data = body.get("data") if isinstance(body.get("data"), dict) else {}
    # O MP assina o `data.id` da query string; o corpo é só reserva.
    id_query = qp.get("data.id") or qp.get("id")
    recurso_id = str(id_query or data.get("id") or body.get("id") or "")

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

    processadores = {
        "preapproval": _processar_preapproval,
        "subscription_preapproval": _processar_preapproval,
        "subscription_authorized_payment": _processar_cobranca_mensal,
        "payment": _processar_pagamento_avulso,
    }
    processar = processadores.get(tipo) if gateway.configurado() else None
    if processar is not None:
        try:
            await processar(db, recurso_id, event_id)
        except GatewayPagamentoError as exc:
            if exc.status_code == 404 and body.get("live_mode") is False:
                # Simulação do painel com id inventado (ex.: "123456"): o recurso
                # não existe e nunca vai existir. Com 503 o MP repetiria à toa.
                # Notificação real (live_mode true) com 404 continua no 503
                # abaixo, para o MP tentar de novo.
                await db.rollback()
                db.add(BillingWebhookEvent(
                    provider="mercadopago", event_id=event_id,
                    event_type=tipo or "desconhecido", payload=body,
                    error_message=f"Recurso inexistente no Mercado Pago (teste): {exc}",
                ))
                await db.commit()
                return {"status": "ignorado"}
            logger.warning("webhook_reconciliacao_falhou: %s", exc)
            # Não grava o evento: com 503 o Mercado Pago reenvia e a
            # reconciliação roda de novo (antes o retry caía em already_processed
            # e o pagamento nunca ativava o plano).
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Reconciliação indisponível, tente novamente",
            )
        evento.processed = True
        evento.processed_at = datetime.now(timezone.utc)

    await db.commit()
    return {"status": "ok"}


async def _processar_preapproval(db: AsyncSession, recurso_id: str, event_id: str) -> None:
    """Assinatura mensal (preapproval): autorizada ativa; cancelada/pausada suspende."""
    pre = await gateway.obter_preapproval(recurso_id)
    pre_status = (pre.get("status") or "").lower()
    valor_mensal = int(
        round(float((pre.get("auto_recurring") or {}).get("transaction_amount") or 0) * 100)
    )
    sub_ref, plano_ref, _ = ler_referencia(pre.get("external_reference"))
    sub = (
        await db.execute(
            select(TenantSubscription).where(TenantSubscription.provider_subscription_id == recurso_id)
        )
    ).scalar_one_or_none()
    if sub is None and sub_ref is not None:
        # 1ª autorização: o checkout não grava mais o id do preapproval.
        sub = (
            await db.execute(select(TenantSubscription).where(TenantSubscription.id == sub_ref))
        ).scalar_one_or_none()
    if sub is None:
        return

    agora = datetime.now(timezone.utc)
    sub.last_event_id = event_id
    sub.last_event_at = agora
    eh_a_atual = sub.provider_subscription_id == recurso_id

    if pre_status == "authorized":
        plano = await _plano_por_slug(db, plano_ref)
        preco = plano.price_monthly if plano is not None else sub.amount
        if valor_mensal and preco is not None and valor_mensal != valor_centavos(preco):
            logger.warning(
                "webhook_valor_divergente sub=%s esperado=%s pago=%s",
                sub.id, valor_centavos(preco), valor_mensal,
            )
            return
        if not eh_a_atual:
            # Nova recorrência (1ª assinatura ou troca de plano/ciclo): para a antiga.
            await _cancelar_recorrencia_antiga(sub, recurso_id)
            sub.provider_subscription_id = recurso_id
            sub.billing_provider = "mercadopago"
            sub.billing_cycle = "mensal"
            if plano is not None:
                sub.plan_id = plano.id
                sub.amount = plano.price_monthly
        fim_atual = _aware(sub.current_period_end)
        ja_ativa = sub.status == "active" and fim_atual is not None and fim_atual > agora
        if not ja_ativa or not eh_a_atual:
            # Recorrência nova vale por cima de um cancelamento anterior.
            sub.cancelled_at = None
        if not ja_ativa:
            # Primeira autorização (ou reativação). Renovações do
            # mês vêm pelo tópico subscription_authorized_payment;
            # outras atualizações do preapproval não esticam o período.
            sub.status = "active"
            sub.current_period_start = agora
            sub.current_period_end = agora + timedelta(days=30)
        await _refletir_plano_no_tenant(db, sub)
    elif pre_status in ("cancelled", "paused"):
        if not eh_a_atual:
            # Aviso de uma recorrência que já foi trocada (ou nunca foi paga):
            # não mexe na assinatura que está valendo.
            return
        fim = _aware(sub.current_period_end)
        if (
            pre_status == "cancelled" and sub.cancelled_at is not None
            and sub.status == "active" and fim is not None and fim > agora
        ):
            # Cancelamento pedido pelo dono: o período pago segue até o fim.
            pass
        elif sub.status in ("active", "trialing", "past_due"):
            sub.status = "suspended"
            if pre_status == "cancelled":
                sub.cancelled_at = agora


async def _processar_cobranca_mensal(db: AsyncSession, recurso_id: str, event_id: str) -> None:
    """Cobrança mensal da assinatura (todo mês).

    Aprovada e com o valor certo → fim do período passa a ser hoje + 30 dias.
    Isso mantém o "cancelar mantém o período pago" correto a partir do 2º mês.
    """
    aut = await gateway.obter_pagamento_autorizado(recurso_id)
    pre_id = str(aut.get("preapproval_id") or "")
    pagamento = aut.get("payment") if isinstance(aut.get("payment"), dict) else {}
    pag_status = (pagamento.get("status") or aut.get("status") or "").lower()
    if not pre_id:
        return
    sub = (
        await db.execute(
            select(TenantSubscription).where(TenantSubscription.provider_subscription_id == pre_id)
        )
    ).scalar_one_or_none()
    if sub is None:
        return
    agora = datetime.now(timezone.utc)
    sub.last_event_id = event_id
    sub.last_event_at = agora
    pago_cent = int(round(float(aut.get("transaction_amount") or 0) * 100))
    if pag_status not in ("approved", "processed"):
        return
    if sub.amount is not None and pago_cent and pago_cent != valor_centavos(sub.amount):
        logger.warning(
            "webhook_valor_divergente sub=%s esperado=%s pago=%s",
            sub.id, valor_centavos(sub.amount), pago_cent,
        )
        return
    if sub.status in ("cancelled", "suspended"):
        return
    if not await _aplicar_uma_vez(db, f"aplicado:authorized_payment:{recurso_id}:aprovado"):
        return
    # max(): a 1ª cobrança chega junto com o preapproval
    # autorizado e não pode virar 60 dias.
    fim_atual = _aware(sub.current_period_end)
    novo_fim = agora + timedelta(days=30)
    if fim_atual is None or fim_atual < novo_fim:
        sub.current_period_start = agora
        sub.current_period_end = novo_fim
    sub.status = "active"
    await _refletir_plano_no_tenant(db, sub)


async def _processar_pagamento_avulso(db: AsyncSession, recurso_id: str, event_id: str) -> None:
    """Ciclos pré-pagos (trimestral/semestral/anual): pagamento único.

    Reconcilia no gateway; casa pelo external_reference e só ativa se aprovado
    E valor == Pix ou cartão esperado para o plano e o ciclo pedidos.
    """
    pag = await gateway.obter_pagamento(recurso_id)
    pag_status = (pag.get("status") or "").lower()
    sub_id, plano_ref, ciclo_ref = ler_referencia(pag.get("external_reference"))
    if sub_id is None:
        return
    sub = (
        await db.execute(select(TenantSubscription).where(TenantSubscription.id == sub_id))
    ).scalar_one_or_none()
    if sub is None:
        return
    agora = datetime.now(timezone.utc)
    sub.last_event_id = event_id
    sub.last_event_at = agora

    if pag_status == "approved":
        plano = await _plano_por_slug(db, plano_ref)
        preco = plano.price_monthly if plano is not None else sub.amount
        ciclo = ciclo_ref or sub.billing_cycle
        pago_cent = int(round(float(pag.get("transaction_amount") or 0) * 100))
        aceitos_cent = {int(round(v * 100)) for v in valores_aceitos(preco or 0, ciclo)}
        if pago_cent not in aceitos_cent:
            # Valor divergente → NÃO ativa (revisão manual via evento).
            logger.warning(
                "webhook_valor_divergente sub=%s ciclo=%s aceitos=%s pago=%s",
                sub.id, ciclo, aceitos_cent, pago_cent,
            )
            return
        if not await _aplicar_uma_vez(db, f"aplicado:payment:{recurso_id}:aprovado"):
            return  # mesmo pagamento, outro formato de aviso: já aplicado
        # Pré-pago confirmado: o mensal anterior (se houver) para de cobrar.
        await _cancelar_recorrencia_antiga(sub, None)
        sub.provider_subscription_id = None
        sub.billing_provider = "mercadopago"
        sub.billing_cycle = ciclo
        if plano is not None:
            sub.plan_id = plano.id
            sub.amount = plano.price_monthly
        ciclo_info = get_ciclo(ciclo) or {"meses": 1}
        sub.status = "active"
        sub.cancelled_at = None
        sub.current_period_start = agora
        sub.current_period_end = agora + timedelta(days=30 * int(ciclo_info["meses"]))
        await _refletir_plano_no_tenant(db, sub)
    elif pag_status in ("refunded", "charged_back"):
        # Estorno/chargeback → suspende (proteção de receita).
        if sub.status in ("active", "trialing", "past_due"):
            sub.status = "suspended"
