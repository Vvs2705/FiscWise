"""
Developer Settings Endpoints — Phase 12: Public API & Webhooks.

Authenticated routes for managing API keys and webhook subscriptions.
All endpoints require a valid JWT (standard FiscWise user session).
"""

import uuid
from typing import List, Optional
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.services import api_key_service, webhook_service
from app.schemas.developer import (
    ApiKeyCreate,
    ApiKeyResponse,
    ApiKeyCreatedResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionUpdate,
    WebhookSubscriptionResponse,
    WebhookSubscriptionCreatedResponse,
    WebhookDeliveryLogResponse,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/developer", tags=["Developer"])


# ──────────────────────────────────────────────────────────
# API Key Endpoints
# ──────────────────────────────────────────────────────────

@router.get("/api-keys", response_model=List[ApiKeyResponse])
async def list_api_keys(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as chaves de API do tenant."""
    return await api_key_service.list_api_keys(db, current_user.tenant_id)


@router.post("/api-keys", response_model=ApiKeyCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_api_key(
    payload: ApiKeyCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria uma nova chave de API.
    A chave completa é retornada UMA VEZ. Guarde-a com segurança.
    """
    api_key, raw_key = await api_key_service.create_api_key(db, payload, current_user.tenant_id)
    return ApiKeyCreatedResponse(
        id=api_key.id,
        name=api_key.name,
        prefix=api_key.prefix,
        is_active=api_key.is_active,
        created_at=api_key.created_at,
        last_used_at=api_key.last_used_at,
        raw_key=raw_key,
    )


@router.delete("/api-keys/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_api_key(
    key_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Revoga (desativa) uma chave de API."""
    success = await api_key_service.revoke_api_key(db, key_id, current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chave de API não encontrada.")


# ──────────────────────────────────────────────────────────
# Webhook Subscription Endpoints
# ──────────────────────────────────────────────────────────

@router.get("/webhooks", response_model=List[WebhookSubscriptionResponse])
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os webhooks configurados do tenant."""
    return await webhook_service.list_webhook_subscriptions(db, current_user.tenant_id)


@router.post("/webhooks", response_model=WebhookSubscriptionCreatedResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    payload: WebhookSubscriptionCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Cria uma nova assinatura de webhook.
    O segredo de assinatura é retornado UMA VEZ. Use-o para verificar payloads recebidos.
    """
    try:
        sub, signing_secret = await webhook_service.create_webhook_subscription(
            db, payload, current_user.tenant_id
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))

    return WebhookSubscriptionCreatedResponse(
        id=sub.id,
        url=sub.url,
        events=sub.events,
        is_active=sub.is_active,
        created_at=sub.created_at,
        signing_secret=signing_secret,
    )


@router.put("/webhooks/{sub_id}", response_model=WebhookSubscriptionResponse)
async def update_webhook(
    sub_id: uuid.UUID,
    payload: WebhookSubscriptionUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza a URL, eventos ou status de uma assinatura de webhook."""
    try:
        sub = await webhook_service.update_webhook_subscription(
            db, sub_id, current_user.tenant_id, payload
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc))
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook não encontrado.")
    return sub


@router.delete("/webhooks/{sub_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    sub_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exclui uma assinatura de webhook."""
    success = await webhook_service.delete_webhook_subscription(db, sub_id, current_user.tenant_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook não encontrado.")


# ──────────────────────────────────────────────────────────
# Delivery Logs Endpoints
# ──────────────────────────────────────────────────────────

@router.get("/webhooks/logs", response_model=List[WebhookDeliveryLogResponse])
async def list_webhook_logs(
    subscription_id: Optional[uuid.UUID] = Query(default=None),
    limit: int = Query(default=50, le=200),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista os logs de entrega de webhooks do tenant (últimos 50 por padrão)."""
    return await webhook_service.list_delivery_logs(
        db, current_user.tenant_id, subscription_id, limit
    )


# ──────────────────────────────────────────────────────────
# Available Events Reference
# ──────────────────────────────────────────────────────────

@router.get("/webhooks/events", response_model=List[str])
async def list_available_events(
    current_user: User = Depends(get_current_user),
):
    """Retorna a lista de tipos de eventos disponíveis para assinatura."""
    from app.schemas.developer import VALID_EVENTS
    return VALID_EVENTS
