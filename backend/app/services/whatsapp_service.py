"""
WhatsApp Service for FiscWise.
Handles message sending, receiving (webhooks), linking to clients,
automated document collection, and converting messages to tasks.
"""

import uuid
import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List

from fastapi import BackgroundTasks
from sqlalchemy import select, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.whatsapp import WhatsAppInbox, WhatsAppMessage
from app.models.operations import AccountingClient, ClientDocument, DeadlineItem
from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)


def _normalize_phone(phone: str) -> str:
    """Normalize phone number to digits only, keeping last 8/9 digits for fuzzy match."""
    if not phone:
        return ""
    digits = "".join(filter(str.isdigit, phone))
    return digits


async def _find_client_by_phone(db: AsyncSession, tenant_id: uuid.UUID, phone: str) -> Optional[AccountingClient]:
    """
    Find accounting client by matching their phone or responsible phone.
    Performs a normalization match.
    """
    normalized_input = _normalize_phone(phone)
    if not normalized_input:
        return None

    # Retrieve all active clients of the tenant to do normalisation matching
    stmt = select(AccountingClient).where(
        (AccountingClient.tenant_id == tenant_id) &
        (AccountingClient.status == "active")
    )
    result = await db.execute(stmt)
    clients = result.scalars().all()

    for client in clients:
        client_phone = _normalize_phone(client.phone or "")
        resp_phone = _normalize_phone(client.responsible_phone or "")
        
        # Match if either phone ends with or matches the input phone suffix (at least 8 digits)
        if len(normalized_input) >= 8:
            suffix = normalized_input[-8:]
            if (client_phone and client_phone.endswith(suffix)) or (resp_phone and resp_phone.endswith(suffix)):
                return client
                
    return None


async def send_whatsapp_message(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    phone_number: str,
    body: str,
    media_url: Optional[str] = None,
    message_type: str = "text",
) -> WhatsAppMessage:
    """
    Sends a WhatsApp message (outbound).
    Creates an inbox if it does not exist.
    """
    # 1. Normalise remote phone
    norm_phone = _normalize_phone(phone_number)
    
    # 2. Get or create inbox
    stmt = select(WhatsAppInbox).where(
        (WhatsAppInbox.tenant_id == tenant_id) &
        (WhatsAppInbox.phone_number == phone_number)
    )
    result = await db.execute(stmt)
    inbox = result.scalar_one_or_none()

    if not inbox:
        # Try to link to a client
        client = await _find_client_by_phone(db, tenant_id, phone_number)
        inbox = WhatsAppInbox(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=client.id if client else None,
            phone_number=phone_number,
            customer_name=client.name if client else f"Contato +{norm_phone}",
            unread_count=0,
            status="active"
        )
        db.add(inbox)
        await db.flush()

    # 3. Simulate message dispatch to WhatsApp provider (Evolution API / Zapi)
    external_message_id = f"mock-msg-{uuid.uuid4()}"
    logger.info(
        "Sending WhatsApp to %s via provider. Body: '%s', Media: %s",
        phone_number, body, media_url
    )

    # 4. Create outbound message
    message = WhatsAppMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        inbox_id=inbox.id,
        direction="outbound",
        sender_name="FiscWise Assistant",
        sender_phone=None,
        message_type=message_type,
        body=body,
        media_url=media_url,
        external_message_id=external_message_id,
        status="sent"
    )
    db.add(message)

    # 5. Update inbox metadata
    inbox.last_message_at = func.now()
    inbox.last_message_preview = body if body else "Arquivo enviado"
    
    await db.commit()
    await db.refresh(message)
    return message


async def process_incoming_webhook(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    sender_phone: str,
    sender_name: str,
    body: str,
    message_type: str = "text",
    media_url: Optional[str] = None,
    external_message_id: Optional[str] = None,
    background_tasks: Optional[BackgroundTasks] = None,
) -> WhatsAppMessage:
    """
    Processes incoming messages from Evolution API/Zapi webhook.
    Auto-links to client and collects documents automatically if media is sent.
    """
    # 1. Get or create inbox
    stmt = select(WhatsAppInbox).where(
        (WhatsAppInbox.tenant_id == tenant_id) &
        (WhatsAppInbox.phone_number == sender_phone)
    )
    result = await db.execute(stmt)
    inbox = result.scalar_one_or_none()

    client = None
    if not inbox:
        # Match client
        client = await _find_client_by_phone(db, tenant_id, sender_phone)
        inbox = WhatsAppInbox(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=client.id if client else None,
            phone_number=sender_phone,
            customer_name=sender_name or (client.name if client else f"Contato +{_normalize_phone(sender_phone)}"),
            unread_count=0,
            status="active"
        )
        db.add(inbox)
        await db.flush()
    else:
        # If client not linked, try matching again in case a new client was registered
        if not inbox.client_id:
            client = await _find_client_by_phone(db, tenant_id, sender_phone)
            if client:
                inbox.client_id = client.id
                inbox.customer_name = client.name
        else:
            stmt_client = select(AccountingClient).where(AccountingClient.id == inbox.client_id)
            client_res = await db.execute(stmt_client)
            client = client_res.scalar_one_or_none()

    # 2. Register incoming message
    message = WhatsAppMessage(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        inbox_id=inbox.id,
        direction="inbound",
        sender_name=sender_name,
        sender_phone=sender_phone,
        message_type=message_type,
        body=body,
        media_url=media_url,
        external_message_id=external_message_id or f"inbound-msg-{uuid.uuid4()}",
        status="delivered"
    )
    db.add(message)

    # 3. Update inbox preview & unread count
    inbox.last_message_at = func.now()
    inbox.last_message_preview = body if body else "Arquivo recebido"
    inbox.unread_count += 1

    # 4. Automated Document Collection:
    # If media file is received and the inbox is linked to a client
    if message_type in ("document", "image") and media_url and inbox.client_id:
        doc_name = body or f"Doc WhatsApp - {datetime.now().strftime('%Y%m%d_%H%M%S')}"
        # Suffix handling
        if message_type == "document" and not doc_name.lower().endswith((".pdf", ".xlsx", ".docx", ".xml")):
            doc_name += ".pdf"
        elif message_type == "image" and not doc_name.lower().endswith((".jpg", ".jpeg", ".png")):
            doc_name += ".png"

        # Create ClientDocument
        document = ClientDocument(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=inbox.client_id,
            name=doc_name,
            document_type="other",
            status="available",
            file_url=media_url,
            parse_status="pending"
        )
        db.add(document)
        await db.flush()

        logger.info(
            "Auto-collected document from WhatsApp: '%s' for Client ID: %s",
            doc_name, inbox.client_id
        )

        # Trigger background document parser if background tasks are provided
        if background_tasks:
            from app.api.v1.endpoints.operations import _parse_document_background
            # Create a mock local file representing the downloaded media
            mock_local_path = f"/tmp/{document.id}_{doc_name}"
            # Write a dummy text or download simulation (for tests/mock purposes)
            background_tasks.add_task(
                _parse_document_background,
                document_id=document.id,
                file_path=mock_local_path,
                file_name=doc_name,
                tenant_id=tenant_id,
            )

    await db.commit()
    await db.refresh(message)
    return message


async def link_inbox_to_client(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    inbox_id: uuid.UUID,
    client_id: Optional[uuid.UUID],
) -> WhatsAppInbox:
    """Links/unlinks a WhatsAppInbox thread to an AccountingClient."""
    stmt = select(WhatsAppInbox).where(
        (WhatsAppInbox.id == inbox_id) &
        (WhatsAppInbox.tenant_id == tenant_id)
    )
    result = await db.execute(stmt)
    inbox = result.scalar_one_or_none()

    if not inbox:
        raise ValueError("Inbox not found")

    if client_id:
        # Verify client exists and belongs to the tenant
        stmt_client = select(AccountingClient).where(
            (AccountingClient.id == client_id) &
            (AccountingClient.tenant_id == tenant_id)
        )
        res_client = await db.execute(stmt_client)
        client = res_client.scalar_one_or_none()
        if not client:
            raise ValueError("Client not found")
        
        inbox.client_id = client_id
        inbox.customer_name = client.name
    else:
        inbox.client_id = None
        # Fallback to phone number naming
        norm_phone = _normalize_phone(inbox.phone_number)
        inbox.customer_name = f"Contato +{norm_phone}"

    await db.commit()
    await db.refresh(inbox)
    return inbox


async def convert_message_to_task(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    message_id: uuid.UUID,
    title: str,
    due_date: date,
    priority: str = "medium",
) -> DeadlineItem:
    """Converts a specific WhatsApp message body into a client's DeadlineItem (task)."""
    # 1. Fetch message and inbox
    stmt = select(WhatsAppMessage).where(
        (WhatsAppMessage.id == message_id) &
        (WhatsAppMessage.tenant_id == tenant_id)
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if not message:
        raise ValueError("Message not found")

    # 2. Get inbox
    stmt_inbox = select(WhatsAppInbox).where(WhatsAppInbox.id == message.inbox_id)
    res_inbox = await db.execute(stmt_inbox)
    inbox = res_inbox.scalar_one_or_none()

    if not inbox or not inbox.client_id:
        raise ValueError("Inbox is not linked to a client. Please link it before creating tasks.")

    # 3. Create DeadlineItem
    task = DeadlineItem(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        client_id=inbox.client_id,
        title=title,
        category="operational",
        due_date=due_date,
        status="pending",
        priority=priority,
        description=f"Criado a partir de mensagem do WhatsApp:\n\n{message.body or '[Sem conteúdo de texto]'}"
    )
    db.add(task)
    
    # Create audit log event
    audit_evt = AuditEvent(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        action="whatsapp.convert_task",
        entity_type="deadline_item",
        entity_id=task.id,
        after_data={"title": title, "due_date": str(due_date), "message_id": str(message_id)}
    )
    db.add(audit_evt)

    await db.commit()
    await db.refresh(task)
    return task
