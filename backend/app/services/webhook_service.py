"""
Webhook Service for FiscWise — Phase 12: Public API & Webhooks.

Handles subscription management, event dispatching (async fire-and-forget),
HMAC-SHA256 payload signing, and delivery logging.

Esquema de assinatura (v1), o mesmo estilo do Stripe:
  X-FiscWise-Signature: t=<unix_ts>,v1=<hex>
  v1 = HMAC-SHA256(chave = segredo cru "whsec_...", msg = f"{t}." + corpo_bruto)
O segredo cru é mostrado uma vez na criação/rotação; no banco fica cifrado
(Fernet, chave derivada de JWT_SECRET_KEY) para o servidor conseguir assinar.
"""

import base64
import uuid
import json
import hmac
import hashlib
import logging
import asyncio
import time
import secrets
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set

import httpx
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.api_webhooks import WebhookSubscription, WebhookDeliveryLog
from app.schemas.developer import WebhookSubscriptionCreate, WebhookSubscriptionUpdate, VALID_EVENTS

logger = logging.getLogger(__name__)

WEBHOOK_TIMEOUT_SECONDS = 10
WEBHOOK_SECRET_BYTES = 32  # 64 hex chars
SIGNATURE_SCHEME = "hmac-sha256-v1"
# Espera antes de cada nova tentativa: 1ª entrega imediata + 3 retries.
RETRY_DELAYS_SECONDS = (1, 5, 25)
_ENC_PREFIX = "enc:v1:"

# Tarefas de entrega em andamento: referência forte para o GC não coletá-las
# no meio (asyncio só guarda referência fraca de tasks soltas).
_background_tasks: Set[asyncio.Task] = set()
_sleep = asyncio.sleep  # trocado nos testes


# ──────────────────────────────────────────────────────────
# Segredo cifrado
# ──────────────────────────────────────────────────────────

def _fernet() -> Fernet:
    from app.core.config import settings

    digest = hashlib.sha256(b"fiscwise-webhook-secret:" + settings.JWT_SECRET_KEY.encode()).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(raw_secret: str) -> str:
    return _ENC_PREFIX + _fernet().encrypt(raw_secret.encode()).decode()


def decrypt_secret(stored: str) -> Optional[str]:
    """Segredo cru a partir do valor guardado; None se for legado (só hash)
    ou se a chave de servidor mudou (JWT_SECRET_KEY rotacionado)."""
    if not stored or not stored.startswith(_ENC_PREFIX):
        return None
    try:
        return _fernet().decrypt(stored[len(_ENC_PREFIX):].encode()).decode()
    except InvalidToken:
        return None


# ──────────────────────────────────────────────────────────
# Subscription Management
# ──────────────────────────────────────────────────────────

def _generate_signing_secret() -> str:
    """Generate a cryptographically secure webhook signing secret."""
    return f"whsec_{secrets.token_hex(WEBHOOK_SECRET_BYTES)}"


async def create_webhook_subscription(
    db: AsyncSession,
    payload: WebhookSubscriptionCreate,
    tenant_id: uuid.UUID,
) -> tuple[WebhookSubscription, str]:
    """
    Create a new webhook subscription.
    Returns (WebhookSubscription ORM object, signing_secret).
    The signing secret is shown once; it is stored encrypted (never in plain
    text) so the server can sign deliveries with it.
    """
    # Validate events
    invalid_events = [e for e in payload.events if e not in VALID_EVENTS]
    if invalid_events:
        raise ValueError(f"Eventos inválidos: {invalid_events}. Permitidos: {VALID_EVENTS}")

    signing_secret = _generate_signing_secret()

    sub = WebhookSubscription(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        url=payload.url,
        secret=encrypt_secret(signing_secret),
        events=payload.events,
        is_active=True,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    logger.info("Webhook subscription created: tenant=%s url=%s", tenant_id, payload.url)
    return sub, signing_secret


async def list_webhook_subscriptions(
    db: AsyncSession,
    tenant_id: uuid.UUID,
) -> List[WebhookSubscription]:
    """List all webhook subscriptions for a tenant."""
    stmt = select(WebhookSubscription).where(
        WebhookSubscription.tenant_id == tenant_id
    ).order_by(WebhookSubscription.created_at)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_webhook_subscription(
    db: AsyncSession,
    sub_id: uuid.UUID,
    tenant_id: uuid.UUID,
    payload: WebhookSubscriptionUpdate,
) -> Optional[WebhookSubscription]:
    """Update an existing webhook subscription."""
    stmt = select(WebhookSubscription).where(
        (WebhookSubscription.id == sub_id) & (WebhookSubscription.tenant_id == tenant_id)
    )
    result = await db.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        return None

    if payload.url is not None:
        sub.url = payload.url
    if payload.events is not None:
        invalid_events = [e for e in payload.events if e not in VALID_EVENTS]
        if invalid_events:
            raise ValueError(f"Eventos inválidos: {invalid_events}")
        sub.events = payload.events
    if payload.is_active is not None:
        sub.is_active = payload.is_active

    await db.commit()
    await db.refresh(sub)
    return sub


async def rotate_webhook_secret(
    db: AsyncSession,
    sub_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> Optional[tuple[WebhookSubscription, str]]:
    """Gera um segredo novo (mostrado uma vez). Também migra assinaturas
    antigas, que só guardavam o hash e por isso não eram verificáveis."""
    stmt = select(WebhookSubscription).where(
        (WebhookSubscription.id == sub_id) & (WebhookSubscription.tenant_id == tenant_id)
    )
    sub = (await db.execute(stmt)).scalar_one_or_none()
    if not sub:
        return None
    signing_secret = _generate_signing_secret()
    sub.secret = encrypt_secret(signing_secret)
    await db.commit()
    await db.refresh(sub)
    return sub, signing_secret


async def delete_webhook_subscription(
    db: AsyncSession,
    sub_id: uuid.UUID,
    tenant_id: uuid.UUID,
) -> bool:
    """Delete a webhook subscription."""
    stmt = select(WebhookSubscription).where(
        (WebhookSubscription.id == sub_id) & (WebhookSubscription.tenant_id == tenant_id)
    )
    result = await db.execute(stmt)
    sub = result.scalar_one_or_none()
    if not sub:
        return False
    await db.delete(sub)
    await db.commit()
    return True


async def list_delivery_logs(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    subscription_id: Optional[uuid.UUID] = None,
    limit: int = 50,
) -> List[WebhookDeliveryLog]:
    """List webhook delivery logs for a tenant."""
    stmt = select(WebhookDeliveryLog).where(
        WebhookDeliveryLog.tenant_id == tenant_id
    ).order_by(WebhookDeliveryLog.created_at.desc()).limit(limit)
    if subscription_id:
        stmt = stmt.where(WebhookDeliveryLog.subscription_id == subscription_id)
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ──────────────────────────────────────────────────────────
# Event Dispatching
# ──────────────────────────────────────────────────────────

def sign_payload(secret: str, payload_bytes: bytes, timestamp: int) -> str:
    """HMAC-SHA256 do segredo CRU sobre f"{timestamp}." + corpo (estilo Stripe)."""
    signed_content = f"{timestamp}.".encode() + payload_bytes
    return hmac.new(secret.encode(), signed_content, hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class _Target:
    """Cópia dos dados da assinatura: a entrega não toca objetos da sessão da request."""
    id: uuid.UUID
    tenant_id: uuid.UUID
    url: str
    secret: str


def _should_retry(status_code: Optional[int]) -> bool:
    if status_code is None:  # erro de rede / timeout
        return True
    return status_code in (408, 429) or status_code >= 500


async def _log_attempt(target: _Target, event: str, body: str, status_code, response_body, duration_ms, success) -> None:
    """Grava a tentativa numa sessão própria (padrão de core/audit.py)."""
    from app.core.deps import get_sessionmaker

    try:
        async with get_sessionmaker()() as db:
            db.add(WebhookDeliveryLog(
                id=uuid.uuid4(),
                tenant_id=target.tenant_id,
                subscription_id=target.id,
                event=event,
                url=target.url,
                status_code=status_code,
                request_body=body,
                response_body=response_body,
                duration_ms=duration_ms,
                success=success,
            ))
            await db.commit()
    except Exception:
        logger.exception("Falha ao gravar log de webhook: sub=%s event=%s", target.id, event)


async def _deliver(target: _Target, event: str, data: Dict[str, Any]) -> bool:
    """Entrega um evento com retry (1 s, 5 s, 25 s). Cada tentativa vira um
    registro em webhook_delivery_logs; o X-FiscWise-Delivery é o mesmo em todas,
    para o receptor descartar duplicatas."""
    delivery_id = str(uuid.uuid4())
    raw_secret = decrypt_secret(target.secret)
    if raw_secret is None and not target.secret.startswith(_ENC_PREFIX):
        # Assinatura criada antes do v1: só o hash foi guardado. Continua
        # assinando como antes (com o hash) para não cortar entregas; a tela
        # mostra "legado" e pede para rotacionar o segredo.
        raw_secret = target.secret
    elif raw_secret is None:
        # Cifrado com outra JWT_SECRET_KEY: não dá para assinar. Não envia.
        await _log_attempt(
            target, event, json.dumps({"event": event, "data": data}, default=str), None,
            "Segredo de assinatura indisponível: rotacione o segredo para voltar a receber.",
            0, False,
        )
        logger.warning("Webhook sem segredo utilizável: sub=%s", target.id)
        return False

    attempts = 1 + len(RETRY_DELAYS_SECONDS)
    for attempt in range(attempts):
        if attempt:
            await _sleep(RETRY_DELAYS_SECONDS[attempt - 1])
        timestamp = int(time.time())
        payload = {"id": delivery_id, "event": event, "timestamp": timestamp, "data": data}
        payload_bytes = json.dumps(payload, default=str).encode()
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "FiscWise-Webhooks/1",
            "X-FiscWise-Event": event,
            "X-FiscWise-Delivery": delivery_id,
            "X-FiscWise-Signature": f"t={timestamp},v1={sign_payload(raw_secret, payload_bytes, timestamp)}",
        }
        status_code: Optional[int] = None
        response_body: Optional[str] = None
        start = time.monotonic()
        try:
            async with httpx.AsyncClient(timeout=WEBHOOK_TIMEOUT_SECONDS, follow_redirects=False) as client:
                resp = await client.post(target.url, content=payload_bytes, headers=headers)
            status_code = resp.status_code
            response_body = (resp.text or "")[:4096]
        except Exception as exc:
            response_body = f"{type(exc).__name__}: {exc}"[:4096]
        duration_ms = int((time.monotonic() - start) * 1000)
        success = status_code is not None and 200 <= status_code < 300
        await _log_attempt(target, event, payload_bytes.decode(), status_code, response_body, duration_ms, success)
        if success:
            return True
        logger.warning(
            "Webhook falhou (tentativa %d/%d): sub=%s event=%s status=%s",
            attempt + 1, attempts, target.id, event, status_code,
        )
        if not _should_retry(status_code):
            return False
    return False


def _spawn(coro) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)
    task.add_done_callback(_background_tasks.discard)
    return task


async def wait_for_deliveries() -> None:
    """Aguarda as entregas pendentes (testes e desligamento ordenado)."""
    while _background_tasks:
        await asyncio.gather(*list(_background_tasks), return_exceptions=True)


async def dispatch_event(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    event: str,
    data: Dict[str, Any],
) -> None:
    """
    Dispatch a webhook event to all active subscriptions for a tenant.

    Chame DEPOIS do commit da operação. A sessão da request só é usada para
    ler as assinaturas; cada entrega roda em tarefa própria, com sessão própria
    para o log, e nunca derruba a operação de negócio.
    """
    try:
        stmt = select(WebhookSubscription).where(
            (WebhookSubscription.tenant_id == tenant_id)
            & (WebhookSubscription.is_active == True)  # noqa: E712
        )
        subscriptions = (await db.execute(stmt)).scalars().all()
        targets = [
            _Target(id=s.id, tenant_id=s.tenant_id, url=s.url, secret=s.secret)
            for s in subscriptions
            if event in (s.events or [])
        ]
    except Exception:
        logger.exception("Falha ao buscar webhooks: tenant=%s event=%s", tenant_id, event)
        return
    if not targets:
        return

    for target in targets:
        _spawn(_deliver(target, event, data))
    logger.info("Dispatching event=%s to %d webhook(s) for tenant=%s", event, len(targets), tenant_id)
