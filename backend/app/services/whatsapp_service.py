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

        # Create ClientDocument. A mídia ainda está no provedor: o arquivo só
        # passa a ser nosso depois de baixado e salvo no storage (ver
        # ingest_whatsapp_media); até lá file_url guarda a URL de origem.
        from app.core import storage as _storage

        can_ingest = bool(background_tasks) and _storage._storage_configured()
        document = ClientDocument(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            client_id=inbox.client_id,
            name=doc_name,
            document_type="other",
            status="available",
            file_url=media_url,
            parse_status="processing" if can_ingest else "skipped",
            parse_error=None if can_ingest else MEDIA_SKIP_NO_STORAGE,
        )
        db.add(document)
        await db.flush()

        logger.info(
            "Auto-collected document from WhatsApp: '%s' for Client ID: %s",
            doc_name, inbox.client_id
        )

        if can_ingest:
            background_tasks.add_task(
                ingest_whatsapp_media,
                document_id=document.id,
                media_url=media_url,
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


# ---------------------------------------------------------------------------
# Mídia recebida: download seguro → storage → parser
# ---------------------------------------------------------------------------
# Antes o documento apontava para a URL do provedor e o parser tentava ler
# /tmp/{id}_{nome}, que nunca era baixado (parse sempre falhava).

MEDIA_MAX_BYTES = 20 * 1024 * 1024
MEDIA_TIMEOUT_S = 15.0
MEDIA_MAX_REDIRECTS = 3
MEDIA_SKIP_NO_STORAGE = "storage não configurado: mídia do WhatsApp não foi baixada"
_MEDIA_TRANSPORT = None  # testes injetam httpx.MockTransport aqui
_BLOCKED_HOST_SUFFIXES = (".local", ".localhost", ".internal", ".lan", ".home.arpa")

# Mesma ideia do core/file_validator: tipo decidido pelos bytes, não pelo header.
_BINARY_MEDIA = (
    ("application/pdf", ".pdf"),
    ("image/png", ".png"),
    ("image/jpeg", ".jpg"),
    ("image/gif", ".gif"),
    ("image/webp", ".webp"),
    ("application/zip", ".zip"),
)


class MediaRejected(Exception):
    """Mídia recusada (host, tamanho, tipo ou rede). Mensagem vai para parse_error."""


def _ip_is_public(ip_text: str) -> bool:
    import ipaddress

    ip = ipaddress.ip_address(ip_text)
    if isinstance(ip, ipaddress.IPv6Address) and ip.ipv4_mapped:
        ip = ip.ipv4_mapped
    return ip.is_global and not ip.is_multicast


async def _resolve_host(host: str) -> list[str]:
    import asyncio
    import socket

    infos = await asyncio.get_running_loop().getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    return [info[4][0] for info in infos]


async def _check_media_url(url: str) -> None:
    """Anti-SSRF: só https, sem credencial/porta estranha, host público."""
    import ipaddress
    from urllib.parse import urlsplit

    parts = urlsplit(url)
    if parts.scheme != "https":
        raise MediaRejected("mídia recusada: só https é aceito")
    host = (parts.hostname or "").rstrip(".").lower()
    if not host or parts.username or parts.password:
        raise MediaRejected("mídia recusada: URL inválida")
    if parts.port not in (None, 443):
        raise MediaRejected("mídia recusada: porta não permitida")
    if host == "localhost" or host.endswith(_BLOCKED_HOST_SUFFIXES) or "." not in host.strip("[]"):
        raise MediaRejected("mídia recusada: host interno")
    try:
        ipaddress.ip_address(host.strip("[]"))
        addrs = [host.strip("[]")]
    except ValueError:
        try:
            addrs = await _resolve_host(host)
        except OSError:
            raise MediaRejected("mídia recusada: host não resolve")
    if not addrs or not all(_ip_is_public(a) for a in addrs):
        raise MediaRejected("mídia recusada: endereço privado ou de metadados")


async def download_media(url: str) -> tuple[bytes, str]:
    """Baixa a mídia com timeout, teto de tamanho e redirects revalidados."""
    import httpx

    async with httpx.AsyncClient(
        timeout=MEDIA_TIMEOUT_S, follow_redirects=False, transport=_MEDIA_TRANSPORT
    ) as client:
        for _ in range(MEDIA_MAX_REDIRECTS + 1):
            await _check_media_url(url)
            try:
                async with client.stream("GET", url) as resp:
                    if resp.is_redirect:
                        location = resp.headers.get("location")
                        if not location:
                            raise MediaRejected("mídia recusada: redirect sem destino")
                        url = str(resp.url.join(location))
                        continue
                    if resp.status_code != 200:
                        raise MediaRejected(f"falha ao baixar mídia (HTTP {resp.status_code})")
                    declared = resp.headers.get("content-length")
                    if declared and declared.isdigit() and int(declared) > MEDIA_MAX_BYTES:
                        raise MediaRejected("mídia recusada: maior que 20 MB")
                    chunks: list[bytes] = []
                    size = 0
                    async for chunk in resp.aiter_bytes():
                        size += len(chunk)
                        if size > MEDIA_MAX_BYTES:
                            raise MediaRejected("mídia recusada: maior que 20 MB")
                        chunks.append(chunk)
                    return b"".join(chunks), resp.headers.get("content-type", "")
            except httpx.HTTPError as exc:
                raise MediaRejected(f"falha ao baixar mídia ({type(exc).__name__})")
    raise MediaRejected("mídia recusada: redirects demais")


def detect_media_type(data: bytes, name: str, declared: str = "") -> tuple[str, str] | None:
    """(mime, extensão) a partir dos bytes; None se não estiver na allowlist."""
    from pathlib import Path

    from app.core.file_validator import matches_mime

    for mime, ext in _BINARY_MEDIA:
        if matches_mime(data, mime):
            if ext == ".zip":
                name_ext = Path(name).suffix.lower()
                if name_ext in (".xlsx", ".docx"):
                    return mime, name_ext
            return mime, ext
    if not matches_mime(data, "text/plain"):
        return None
    head = data[:2048].lstrip(b"\xef\xbb\xbf \t\r\n")
    if b"<OFX>" in data[:65536].upper():
        return "application/x-ofx", ".ofx"
    if head.startswith(b"<"):
        return "application/xml", ".xml"
    if "csv" in declared.lower() or Path(name).suffix.lower() == ".csv":
        return "text/csv", ".csv"
    return "text/plain", ".txt"


async def ingest_whatsapp_media(document_id: uuid.UUID, media_url: str, tenant_id: uuid.UUID) -> None:
    """Background: baixa a mídia, sobe para documents/<tenant>/..., agenda o parser."""
    import tempfile
    from pathlib import Path

    from app.core import storage as _storage
    from app.core.deps import _set_current_tenant_context, get_sessionmaker
    from app.core.document_links import DOCUMENTS_BUCKET, storage_ref

    async def _finish(**fields: Any) -> Optional[ClientDocument]:
        async with get_sessionmaker()() as db:
            await _set_current_tenant_context(db, tenant_id)
            res = await db.execute(
                select(ClientDocument).where(
                    (ClientDocument.id == document_id) & (ClientDocument.tenant_id == tenant_id)
                )
            )
            doc = res.scalar_one_or_none()
            if doc is None:
                return None
            for key, value in fields.items():
                setattr(doc, key, value)
            await db.commit()
            await db.refresh(doc)
            return doc

    async with get_sessionmaker()() as db:
        await _set_current_tenant_context(db, tenant_id)
        res = await db.execute(
            select(ClientDocument.name).where(
                (ClientDocument.id == document_id) & (ClientDocument.tenant_id == tenant_id)
            )
        )
        name = res.scalar_one_or_none()
    if name is None:
        return

    try:
        data, declared = await download_media(media_url)
        detected = detect_media_type(data, name, declared)
        if detected is None:
            raise MediaRejected("mídia recusada: tipo de arquivo não permitido")
        mime, ext = detected
        path = f"{tenant_id}/{uuid.uuid4().hex}{ext}"
        await _storage.upload_bytes(DOCUMENTS_BUCKET, path, data, mime)
    except MediaRejected as exc:
        logger.warning("Mídia do WhatsApp recusada (doc %s): %s", document_id, exc)
        await _finish(parse_status="failed", parse_error=str(exc))
        return
    except Exception:  # noqa: BLE001 — storage fora: registra e não derruba o worker
        logger.exception("Falha ao salvar mídia do WhatsApp (doc %s)", document_id)
        await _finish(parse_status="failed", parse_error="falha ao salvar mídia no storage")
        return

    if Path(name).suffix.lower() != ext:
        name = f"{Path(name).stem}{ext}"
    await _finish(file_url=storage_ref(path), name=name, parse_status="processing", parse_error=None)

    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        tmp.write(data)
        tmp_path = tmp.name
    from app.api.v1.endpoints.operations import _parse_document_background

    await _parse_document_background(document_id, tmp_path, name, tenant_id)
