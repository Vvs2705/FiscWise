"""
WhatsApp Business API Router for FiscWise.
Provides access to unified messaging threads, inboxes, webhook triggers,
client isolation, and converting messages to tasks.
"""

import uuid
from datetime import date
from typing import Optional, List
import logging

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, get_db
from app.models.user import User
from app.models.whatsapp import WhatsAppInbox, WhatsAppMessage
from app.services import whatsapp_service
from app.schemas.whatsapp import (
    SendWhatsAppRequest,
    LinkInboxRequest,
    ConvertTaskRequest,
    WhatsAppWebhookPayload,
    WhatsAppMessageOut,
    WhatsAppInboxOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/whatsapp", tags=["WhatsApp Inbox"])


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/inboxes", response_model=List[WhatsAppInboxOut])
async def list_inboxes(
    client_id: Optional[uuid.UUID] = Query(default=None),
    status_filter: Optional[str] = Query(default="active", alias="status"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WhatsAppInboxOut]:
    """
    Lista as conversas (inboxes) de WhatsApp correspondentes ao tenant do usuário autenticado.
    Suporta filtragem por cliente ou status (active, archived).
    """
    stmt = (
        select(WhatsAppInbox)
        .where(
            (WhatsAppInbox.tenant_id == current_user.tenant_id) &
            (WhatsAppInbox.status == status_filter)
        )
        .order_by(desc(WhatsAppInbox.last_message_at))
    )

    if client_id:
        stmt = stmt.where(WhatsAppInbox.client_id == client_id)

    result = await db.execute(stmt)
    inboxes = result.scalars().all()

    return [
        WhatsAppInboxOut(
            id=i.id,
            tenant_id=i.tenant_id,
            client_id=i.client_id,
            phone_number=i.phone_number,
            customer_name=i.customer_name,
            last_message_at=i.last_message_at,
            last_message_preview=i.last_message_preview,
            unread_count=i.unread_count,
            status=i.status,
            created_at=i.created_at,
            updated_at=i.updated_at,
        )
        for i in inboxes
    ]


@router.get("/inboxes/{inbox_id}/messages", response_model=List[WhatsAppMessageOut])
async def list_messages(
    inbox_id: uuid.UUID,
    limit: int = Query(default=50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[WhatsAppMessageOut]:
    """
    Retorna o histórico de mensagens de uma conversa específica do WhatsApp.
    Zera o contador de mensagens não lidas ao consultar.
    """
    # 1. Verifica se a conversa pertence ao tenant do usuário
    stmt_inbox = select(WhatsAppInbox).where(
        (WhatsAppInbox.id == inbox_id) &
        (WhatsAppInbox.tenant_id == current_user.tenant_id)
    )
    res_inbox = await db.execute(stmt_inbox)
    inbox = res_inbox.scalar_one_or_none()

    if not inbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        )

    # 2. Zera mensagens não lidas
    if inbox.unread_count > 0:
        inbox.unread_count = 0
        await db.commit()

    # 3. Busca histórico de mensagens
    stmt_msg = (
        select(WhatsAppMessage)
        .where(
            (WhatsAppMessage.inbox_id == inbox_id) &
            (WhatsAppMessage.tenant_id == current_user.tenant_id)
        )
        .order_by(desc(WhatsAppMessage.created_at))
        .limit(limit)
    )
    result_msg = await db.execute(stmt_msg)
    messages = result_msg.scalars().all()

    # Retorna em ordem cronológica (mais antiga para mais recente)
    messages.reverse()

    return [
        WhatsAppMessageOut(
            id=m.id,
            tenant_id=m.tenant_id,
            inbox_id=m.inbox_id,
            direction=m.direction,
            sender_name=m.sender_name,
            sender_phone=m.sender_phone,
            message_type=m.message_type,
            body=m.body,
            media_url=m.media_url,
            external_message_id=m.external_message_id,
            status=m.status,
            created_at=m.created_at,
        )
        for m in messages
    ]


@router.post("/inboxes/{inbox_id}/send", response_model=WhatsAppMessageOut)
async def send_message(
    inbox_id: uuid.UUID,
    req: SendWhatsAppRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WhatsAppMessageOut:
    """
    Envia uma mensagem de WhatsApp para o cliente correspondente à conversa.
    Simula o envio externo e insere no banco.
    """
    # 1. Verifica se a conversa pertence ao tenant do usuário
    stmt_inbox = select(WhatsAppInbox).where(
        (WhatsAppInbox.id == inbox_id) &
        (WhatsAppInbox.tenant_id == current_user.tenant_id)
    )
    res_inbox = await db.execute(stmt_inbox)
    inbox = res_inbox.scalar_one_or_none()

    if not inbox:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversa não encontrada",
        )

    # 2. Executa o envio através do serviço
    message = await whatsapp_service.send_whatsapp_message(
        db=db,
        tenant_id=current_user.tenant_id,
        phone_number=inbox.phone_number,
        body=req.body,
        media_url=req.media_url,
        message_type=req.message_type
    )

    return WhatsAppMessageOut(
        id=message.id,
        tenant_id=message.tenant_id,
        inbox_id=message.inbox_id,
        direction=message.direction,
        sender_name=message.sender_name,
        sender_phone=message.sender_phone,
        message_type=message.message_type,
        body=message.body,
        media_url=message.media_url,
        external_message_id=message.external_message_id,
        status=message.status,
        created_at=message.created_at,
    )


@router.post("/inboxes/{inbox_id}/link", response_model=WhatsAppInboxOut)
async def link_inbox_client(
    inbox_id: uuid.UUID,
    req: LinkInboxRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> WhatsAppInboxOut:
    """
    Associa ou desassocia uma conversa de WhatsApp a um cliente contábil específico (AccountingClient).
    """
    try:
        inbox = await whatsapp_service.link_inbox_to_client(
            db=db,
            tenant_id=current_user.tenant_id,
            inbox_id=inbox_id,
            client_id=req.client_id
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return WhatsAppInboxOut(
        id=inbox.id,
        tenant_id=inbox.tenant_id,
        client_id=inbox.client_id,
        phone_number=inbox.phone_number,
        customer_name=inbox.customer_name,
        last_message_at=inbox.last_message_at,
        last_message_preview=inbox.last_message_preview,
        unread_count=inbox.unread_count,
        status=inbox.status,
        created_at=inbox.created_at,
        updated_at=inbox.updated_at,
    )


@router.post("/messages/{message_id}/convert-task")
async def convert_to_task(
    message_id: uuid.UUID,
    req: ConvertTaskRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Converte uma mensagem recebida em uma nova tarefa (DeadlineItem) vinculada ao cliente.
    A conversa correspondente precisa estar vinculada a um cliente.
    """
    try:
        task = await whatsapp_service.convert_message_to_task(
            db=db,
            tenant_id=current_user.tenant_id,
            message_id=message_id,
            title=req.title,
            due_date=req.due_date,
            priority=req.priority
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    return {
        "status": "success",
        "message": "Mensagem convertida em tarefa com sucesso",
        "task_id": str(task.id),
        "title": task.title,
        "due_date": task.due_date.isoformat(),
    }


@router.post("/webhooks/{tenant_id}")
async def receive_incoming_webhook(
    tenant_id: uuid.UUID,
    payload: WhatsAppWebhookPayload,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Endpoint público (excluído do middleware de Tenant e Auth) para receber
    mensagens enviadas por clientes via Evolution API / Zapi.
    
    Identifica o tenant pelo path parameter '{tenant_id}'.
    """
    logger.info("WhatsApp webhook received for tenant %s: %s", tenant_id, payload.sender_phone)
    
    try:
        # Set the current tenant ID in session if DB session has set_context helper
        from app.core.deps import _set_current_tenant_context
        await _set_current_tenant_context(db, tenant_id)
    except Exception:
        pass  # ignore if not running with context helper / SQLite

    message = await whatsapp_service.process_incoming_webhook(
        db=db,
        tenant_id=tenant_id,
        sender_phone=payload.sender_phone,
        sender_name=payload.sender_name,
        body=payload.body,
        message_type=payload.message_type,
        media_url=payload.media_url,
        external_message_id=payload.external_message_id,
        background_tasks=background_tasks
    )

    return {
        "status": "received",
        "message_id": str(message.id),
        "inbox_id": str(message.inbox_id),
    }
