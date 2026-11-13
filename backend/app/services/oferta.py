"""Oferta de reconquista para quem não assinou depois do teste grátis.

Regras do dono (13/11/2026):
- 5 dias depois de o teste vencer, e-mail com a oferta, válida por 7 dias;
  lembrete "última chance" no 6º dia da oferta (11 dias depois de vencer).
- Mensal no cartão: 15% só no 1º mês (depois preço cheio, recorrente).
  Anual: 25% no total, no Pix ou no cartão em até 6x (app.core.pricing).
- Só para escritório que nunca pagou, uma vez por escritório
  (retention_offers.tenant_id é único). Dono descadastrado não recebe.

Mensal: o Mercado Pago não tem preço de 1º período. O preapproval nasce com
o valor promocional e, quando a 1ª cobrança é aprovada, volta ao preço cheio
com PUT /preapproval/{id} (recurso oficial). Se o PUT falhar, a rotina diária
tenta de novo (`reconciliar_reajustes`).
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any, Optional

import pytz
from jose import JWTError, jwt
from sqlalchemy import and_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.pricing import preco_oferta
from app.models.billing import RetentionOffer, TenantSubscription
from app.models.plan import Plan
from app.models.user import User, UserRole

logger = logging.getLogger(__name__)

TZ_BR = pytz.timezone("America/Sao_Paulo")

DIAS_APOS_VENCER = 5      # oferta sai 5 dias depois de o teste vencer
VALIDADE_DIAS = 7         # e vale 7 dias
LEMBRETE_APOS_DIAS = 6    # lembrete no 6º dia da oferta
JANELA_MAX_DIAS = 60      # depois disso os dados podem ser excluídos: sem oferta

STATUS_ENVIADA = "enviada"
STATUS_OPTOUT = "optout"
STATUS_ACEITA = "aceita"

_PROPOSITO_DESCADASTRO = "descadastro"


# ── Token de descadastro ─────────────────────────────────────────────────────

def montar_token_descadastro(user_id: uuid.UUID | str) -> str:
    """Token do link "não quero mais receber ofertas" (sem expiração curta).

    `purpose` diferente de "access": get_current_user recusa, então o token
    não serve para entrar no sistema.
    """
    payload = {"sub": str(user_id), "purpose": _PROPOSITO_DESCADASTRO,
               "iat": int(datetime.now(timezone.utc).timestamp())}
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def ler_token_descadastro(token: str) -> Optional[uuid.UUID]:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError:
        return None
    if payload.get("purpose") != _PROPOSITO_DESCADASTRO:
        return None
    try:
        return uuid.UUID(str(payload.get("sub")))
    except ValueError:
        return None


# ── Consultas ────────────────────────────────────────────────────────────────

def _aware(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is not None and dt.tzinfo is None:  # SQLite devolve sem fuso
        return dt.replace(tzinfo=timezone.utc)
    return dt


def oferta_esta_vigente(oferta: Optional[RetentionOffer], agora: Optional[datetime] = None) -> bool:
    if oferta is None or oferta.status != STATUS_ENVIADA or oferta.accepted_at is not None:
        return False
    fim = _aware(oferta.expires_at)
    return fim is not None and fim > (agora or datetime.now(timezone.utc))


async def oferta_vigente(db: AsyncSession, tenant_id: uuid.UUID,
                         agora: Optional[datetime] = None) -> Optional[RetentionOffer]:
    oferta = (
        await db.execute(select(RetentionOffer).where(RetentionOffer.tenant_id == tenant_id))
    ).scalar_one_or_none()
    return oferta if oferta_esta_vigente(oferta, agora) else None


async def planos_da_oferta(db: AsyncSession) -> list[Plan]:
    """Planos pagos ativos (o Gratuito e planos sem preço ficam de fora)."""
    planos = (
        await db.execute(select(Plan).where(Plan.active.is_(True)).order_by(Plan.price_monthly))
    ).scalars().all()
    return [p for p in planos if p.slug != "free" and p.price_monthly and float(p.price_monthly) > 0]


def precos_da_oferta(planos: list[Plan]) -> list[dict[str, Any]]:
    return [{"plan_slug": p.slug, "plan_name": p.name, **preco_oferta(p.price_monthly)} for p in planos]


def reason_oferta_mensal(plano_nome: str, preco_mensal: Decimal | float) -> str:
    o = preco_oferta(preco_mensal)
    return (
        f"FiscWise {plano_nome} — 1º mês R$ {_brl(o['mensal_promo'])}, "
        f"depois R$ {_brl(o['mensal_cheio'])}/mês"
    )


def _brl(v: float) -> str:
    return f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


async def _dono(db: AsyncSession, tenant_id: uuid.UUID) -> Optional[User]:
    return await db.scalar(
        select(User).where(
            User.tenant_id == tenant_id,
            User.role == UserRole.OWNER,
            User.is_active.is_(True),
        ).order_by(User.created_at).limit(1)
    )


# ── Rotina diária ────────────────────────────────────────────────────────────

async def _enviar(db: AsyncSession, *, oferta: RetentionOffer, dono: User, marco: str,
                  planos: list[Plan]) -> bool:
    from app.services.email_service import render_oferta_email, send_email

    app_url = settings.APP_URL.rstrip("/")
    api_url = settings.PUBLIC_URL.rstrip("/")
    fim = _aware(oferta.expires_at)
    assunto, html = render_oferta_email(
        marco,
        precos=precos_da_oferta(planos),
        validade_label=fim.astimezone(TZ_BR).strftime("%d/%m/%Y") if fim else "",
        link_assinar=f"{app_url}/assinatura?oferta=1",
        link_descadastro=f"{api_url}/api/v1/marketing/descadastro?token={montar_token_descadastro(dono.id)}",
    )
    return await send_email(
        to=dono.email, subject=assunto, html=html,
        idempotency_key=f"oferta:{oferta.tenant_id}:{marco}",
    )


async def enviar_ofertas_novas(db: AsyncSession, agora: datetime) -> dict:
    """Cria e envia a oferta a quem venceu o teste há 5–60 dias e nunca pagou."""
    from app.core.deps import _set_current_tenant_context

    counts = {"sent": 0, "optout": 0, "no_owner": 0, "failed": 0, "duplicate": 0}
    planos = await planos_da_oferta(db)
    if not planos:
        return counts
    subs = (
        await db.execute(
            select(TenantSubscription).where(
                and_(
                    TenantSubscription.status == "trialing",
                    TenantSubscription.provider_subscription_id.is_(None),
                    TenantSubscription.current_period_end.is_(None),
                    TenantSubscription.trial_ends_at.is_not(None),
                    TenantSubscription.trial_ends_at <= agora - timedelta(days=DIAS_APOS_VENCER),
                    TenantSubscription.trial_ends_at >= agora - timedelta(days=JANELA_MAX_DIAS),
                )
            )
        )
    ).scalars().all()
    ja_tem = set(
        (await db.execute(select(RetentionOffer.tenant_id))).scalars().all()
    )
    # Só os ids: um rollback no meio do laço expira os objetos carregados.
    alvos = [s.tenant_id for s in subs if s.tenant_id not in ja_tem]
    for tenant_id in alvos:
        await _set_current_tenant_context(db, tenant_id)
        oferta = RetentionOffer(tenant_id=tenant_id, status="criada")
        db.add(oferta)
        try:
            await db.flush()
        except IntegrityError:
            await db.rollback()
            counts["duplicate"] += 1
            continue
        dono = await _dono(db, tenant_id)
        if dono is None:
            await db.rollback()
            counts["no_owner"] += 1
            continue
        if dono.marketing_opt_out_at is not None:
            oferta.status = STATUS_OPTOUT  # nunca recebe (fica registrado)
            await db.commit()
            counts["optout"] += 1
            continue
        oferta.sent_at = agora
        oferta.expires_at = agora + timedelta(days=VALIDADE_DIAS)
        oferta.status = STATUS_ENVIADA
        if await _enviar(db, oferta=oferta, dono=dono, marco="oferta", planos=planos):
            await db.commit()
            counts["sent"] += 1
        else:
            # Sem envio (Resend fora ou desligado): desfaz, tenta na próxima rodada.
            await db.rollback()
            counts["failed"] += 1
    return counts


async def enviar_lembretes(db: AsyncSession, agora: datetime) -> dict:
    """Lembrete "última chance" no 6º dia da oferta (uma vez)."""
    from app.core.deps import _set_current_tenant_context

    counts = {"sent": 0, "optout": 0, "failed": 0}
    planos = await planos_da_oferta(db)
    ofertas = (
        await db.execute(
            select(RetentionOffer).where(
                and_(
                    RetentionOffer.status == STATUS_ENVIADA,
                    RetentionOffer.accepted_at.is_(None),
                    RetentionOffer.reminder_sent_at.is_(None),
                    RetentionOffer.expires_at > agora,
                )
            )
        )
    ).scalars().all()
    hoje = agora.astimezone(TZ_BR).date()
    alvos = []
    for oferta in ofertas:
        enviada = _aware(oferta.sent_at)
        if enviada is not None and (hoje - enviada.astimezone(TZ_BR).date()).days >= LEMBRETE_APOS_DIAS:
            alvos.append((oferta.id, oferta.tenant_id))
    for oferta_id, tenant_id in alvos:
        await _set_current_tenant_context(db, tenant_id)
        oferta = await db.get(RetentionOffer, oferta_id)
        if oferta is None:
            continue
        dono = await _dono(db, tenant_id)
        if dono is None or dono.marketing_opt_out_at is not None:
            counts["optout"] += 1
            continue
        oferta.reminder_sent_at = agora
        if await _enviar(db, oferta=oferta, dono=dono, marco="lembrete", planos=planos):
            await db.commit()
            counts["sent"] += 1
        else:
            await db.rollback()
            counts["failed"] += 1
    return counts


async def reajustar_para_preco_cheio(db: AsyncSession, oferta: RetentionOffer) -> bool:
    """PUT do preapproval para o preço cheio. Falha fica para a reconciliação."""
    from app.services.mercadopago import GatewayPagamentoError, gateway

    if not oferta.preapproval_id or oferta.full_amount is None:
        return False
    try:
        await gateway.atualizar_valor_assinatura(oferta.preapproval_id, oferta.full_amount)
    except GatewayPagamentoError as exc:
        logger.error(
            "oferta_reajuste_falhou tenant=%s pre=%s: %s (a rotina diária tenta de novo)",
            oferta.tenant_id, oferta.preapproval_id, exc,
        )
        return False
    oferta.price_bumped_at = datetime.now(timezone.utc)
    logger.info("oferta_reajustada tenant=%s pre=%s valor=%s",
                oferta.tenant_id, oferta.preapproval_id, oferta.full_amount)
    return True


async def reconciliar_reajustes(db: AsyncSession, agora: datetime) -> dict:
    """Mensal aceito com a 1ª cobrança feita e o preço ainda promocional → PUT.

    Cobre o PUT que falhou e o caso em que o aviso da 1ª cobrança chegou antes
    da autorização (o webhook não achou a assinatura e não reajustou).
    """
    from app.services.mercadopago import GatewayPagamentoError, gateway

    counts = {"bumped": 0, "pending": 0, "failed": 0}
    ofertas = (
        await db.execute(
            select(RetentionOffer).where(
                and_(
                    RetentionOffer.status == STATUS_ACEITA,
                    RetentionOffer.accepted_cycle == "mensal",
                    RetentionOffer.preapproval_id.is_not(None),
                    RetentionOffer.price_bumped_at.is_(None),
                )
            )
        )
    ).scalars().all()
    for oferta in ofertas:
        cobrou = oferta.promo_charged_at is not None
        if not cobrou:
            try:
                pre = await gateway.obter_preapproval(oferta.preapproval_id)
            except GatewayPagamentoError as exc:
                logger.warning("oferta_reconciliacao_consulta_falhou pre=%s: %s", oferta.preapproval_id, exc)
                counts["failed"] += 1
                continue
            resumo = pre.get("summarized") or {}
            cobrou = int(resumo.get("charged_quantity") or 0) >= 1
            if cobrou:
                oferta.promo_charged_at = agora
        if not cobrou:
            counts["pending"] += 1
            continue
        if await reajustar_para_preco_cheio(db, oferta):
            counts["bumped"] += 1
        else:
            counts["failed"] += 1
        await db.commit()
    return counts
