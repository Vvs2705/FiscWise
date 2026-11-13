"""Client Portal Endpoints for FiscWise

Handles client portal invitations, magic link authentication, and client data.
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import AliasChoices, BaseModel, EmailStr, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.plan_access import FEATURE_PORTAL_CLIENTE, ensure_can_add_document, ensure_feature
from app.models.portal import PortalMagicToken
from app.models.user import User, UserRole
from app.models.operations import ClientPortalInvite, InviteStatus, AccountingClient
from app.services import email_service
from app.core.auth_rate_limiter import auth_rate_limiter, get_client_ip
from app.core.config import settings
from app.core.security import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portal", tags=["Client Portal"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normaliza para UTC com fuso: o Postgres devolve aware, o SQLite naive.

    Comparar naive com aware levanta TypeError (era o 500 dos convites no PG).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _is_expired(dt: Optional[datetime]) -> bool:
    exp = _as_utc(dt)
    return exp is not None and _now() > exp


class InviteClientRequest(BaseModel):
    """Request to invite a client to the portal."""
    client_id: uuid.UUID
    email: EmailStr = Field(..., description="Client contact email")


class InviteClientResponse(BaseModel):
    """Response after inviting a client."""
    # O model tem `id`; sem o alias o from_orm falhava e POST /invites dava 500.
    invite_id: uuid.UUID = Field(validation_alias=AliasChoices("invite_id", "id"))
    client_id: uuid.UUID
    email: str
    status: str
    expires_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class AcceptInviteRequest(BaseModel):
    """Request to accept a portal invitation."""
    invite_id: uuid.UUID
    password: str = Field(..., min_length=8, description="Password for new portal account")
    full_name: str = Field(..., min_length=1, max_length=255)


class AcceptInviteResponse(BaseModel):
    """Response after accepting an invitation."""
    access_token: str
    token_type: str
    user_id: uuid.UUID


@router.post("/invites", response_model=InviteClientResponse, status_code=status.HTTP_201_CREATED)
async def invite_client(
    request: InviteClientRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> InviteClientResponse:
    """
    Invite a client to access the portal.

    Only OWNER and ADMIN users can invite clients.
    """
    # Check authorization
    if not current_user.is_admin_or_owner():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only administrators can invite clients"
        )
    await ensure_feature(db, current_user.tenant_id, FEATURE_PORTAL_CLIENTE, current_user.email)

    # Verify client exists and belongs to tenant
    result = await db.execute(
        select(AccountingClient).where(
            and_(
                AccountingClient.id == request.client_id,
                AccountingClient.tenant_id == current_user.tenant_id
            )
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Client not found"
        )

    # Check if invite already exists and is active
    result = await db.execute(
        select(ClientPortalInvite).where(
            and_(
                ClientPortalInvite.client_id == request.client_id,
                ClientPortalInvite.email == request.email,
                ClientPortalInvite.status == InviteStatus.PENDING
            )
        )
    )
    existing_invite = result.scalar_one_or_none()

    if existing_invite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An active invitation already exists for this email"
        )

    # Create invitation (valid for 30 days)
    invite = ClientPortalInvite(
        tenant_id=current_user.tenant_id,
        client_id=request.client_id,
        email=request.email,
        status=InviteStatus.PENDING,
        invited_by=current_user.id,
        expires_at=_now() + timedelta(days=30)
    )

    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    return InviteClientResponse.from_orm(invite)


@router.get("/invites/{invite_id}", response_model=InviteClientResponse)
async def get_invite(
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db)
) -> InviteClientResponse:
    """
    Get invitation details (public endpoint for invited users).
    """
    result = await db.execute(
        select(ClientPortalInvite).where(ClientPortalInvite.id == invite_id)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Check if expired
    if _is_expired(invite.expires_at):
        invite.status = InviteStatus.EXPIRED
        db.add(invite)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired"
        )

    if invite.status != InviteStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation has been {invite.status}"
        )

    return InviteClientResponse.from_orm(invite)


@router.post("/invites/{invite_id}/accept", response_model=AcceptInviteResponse)
async def accept_invite(
    invite_id: uuid.UUID,
    request: AcceptInviteRequest,
    db: AsyncSession = Depends(get_db)
) -> AcceptInviteResponse:
    """
    Accept a portal invitation and create a client account.

    Creates a new CLIENT user linked to the accounting client.
    """
    from app.core.security import get_password_hash

    # Get invitation
    result = await db.execute(
        select(ClientPortalInvite).where(ClientPortalInvite.id == invite_id)
    )
    invite = result.scalar_one_or_none()

    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found"
        )

    # Validate invitation
    if invite.status != InviteStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invitation has been {invite.status}"
        )

    if _is_expired(invite.expires_at):
        invite.status = InviteStatus.EXPIRED
        db.add(invite)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Invitation has expired"
        )

    # Convite feito antes de o escritório perder o recurso não cria acesso novo.
    await ensure_feature(db, invite.tenant_id, FEATURE_PORTAL_CLIENTE)

    # Check if user with this email already exists
    result = await db.execute(
        select(User).where(
            and_(
                User.email == invite.email,
                User.tenant_id == invite.tenant_id
            )
        )
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists"
        )

    # Create client user
    client_user = User(
        tenant_id=invite.tenant_id,
        email=invite.email,
        hashed_password=get_password_hash(request.password),
        full_name=request.full_name,
        role=UserRole.CLIENT,
        is_active=True
    )

    # flush antes de ler o id: o default uuid só é aplicado no flush, e sem isso
    # portal_user_id ficava None e o /portal/my-data não achava o cliente.
    db.add(client_user)
    await db.flush()

    # Update client with portal_user_id
    client = (
        await db.execute(
            select(AccountingClient).where(
                AccountingClient.id == invite.client_id,
                AccountingClient.tenant_id == invite.tenant_id,
            )
        )
    ).scalar_one()
    client.portal_user_id = client_user.id

    # Mark invitation as accepted
    invite.status = InviteStatus.ACCEPTED
    invite.accepted_at = _now()

    db.add(client_user)
    db.add(client)
    db.add(invite)
    await db.commit()

    # Generate access token
    access_token = create_access_token(
        user_id=str(client_user.id),
        tenant_id=str(invite.tenant_id),
        role=UserRole.CLIENT.value
    )

    return AcceptInviteResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=client_user.id
    )


@router.get("/my-data")
async def get_my_data(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get client's own data (for CLIENT role users).

    Returns the accounting client information and associated resources.
    """
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only for client users"
        )

    # Find the accounting client linked to this user
    result = await db.execute(
        select(AccountingClient).where(
            and_(
                AccountingClient.portal_user_id == current_user.id,
                AccountingClient.tenant_id == current_user.tenant_id
            )
        )
    )
    client = result.scalar_one_or_none()

    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No client data found for this user"
        )

    return {
        "id": str(client.id),
        "name": client.name,
        "document": client.document,
        "entity_type": client.entity_type,
        "tax_regime": client.tax_regime,
        "email": client.email,
        "phone": client.phone,
        "status": client.status
    }


# ---------------------------------------------------------------------------
# Portal preview (staff view of one client's portal)
# ---------------------------------------------------------------------------


# Status de ClientDocument que significam "o escritório pediu e falta o arquivo".
_DOCUMENT_REQUESTED = ("missing", "expired")
# Itens do checklist ainda em aberto (rejeitado = cliente precisa reenviar).
_CHECKLIST_OPEN = ("pending", "rejected")


async def _sign_portal_files(tenant_id: uuid.UUID, documents: list, guides: list) -> tuple[dict, dict]:
    """URLs assinadas (curtas) para o cliente baixar documentos e guias.

    Falha do storage não derruba o portal: o item só fica sem link.
    """
    from app.core import storage as _storage
    from app.core.document_links import DOCUMENTS_BUCKET, SIGNED_URL_TTL, object_path_for

    doc_urls: dict[int, str] = {}
    doc_paths = {i: object_path_for(d.file_url, tenant_id) for i, d in enumerate(documents)}
    doc_paths = {i: p for i, p in doc_paths.items() if p}
    if doc_paths:
        try:
            signed = await _storage.get_signed_urls(
                DOCUMENTS_BUCKET, list(doc_paths.values()), ttl=SIGNED_URL_TTL
            )
            doc_urls = {i: signed[p] for i, p in doc_paths.items() if p in signed}
        except Exception:  # noqa: BLE001
            logger.exception("Portal: falha ao assinar documentos (tenant %s)", tenant_id)

    guide_urls: dict[str, str] = {}
    guide_paths = [
        g.pdf_storage_path for g in guides
        if g.pdf_storage_path and ".." not in g.pdf_storage_path.split("/")
    ]
    if guide_paths:
        try:
            guide_urls = await _storage.get_signed_urls("guides", guide_paths, ttl=SIGNED_URL_TTL)
        except Exception:  # noqa: BLE001
            logger.exception("Portal: falha ao assinar guias (tenant %s)", tenant_id)
    return doc_urls, guide_urls


async def _portal_payload(db: AsyncSession, tenant_id: uuid.UUID, client: AccountingClient) -> dict:
    """Agrega o que o portal mostra de UM cliente.

    Toda consulta filtra por client.id E tenant_id: quem chama já resolveu
    `client` dentro do escritório certo, e aqui nada vaza de outro cliente.
    """
    from app.models.operations import ClientDocument, DeadlineItem
    from app.models.obligation import DocumentChecklistItem
    from app.domain.guias.models import TaxGuide
    from app.domain.monthly_closing.models import MonthlyClosing

    client_id = client.id

    closing_result = await db.execute(
        select(MonthlyClosing)
        .where(
            and_(
                MonthlyClosing.client_id == client_id,
                MonthlyClosing.tenant_id == tenant_id,
            )
        )
        .order_by(MonthlyClosing.competence.desc())
        .limit(1)
    )
    closing = closing_result.scalar_one_or_none()

    docs_result = await db.execute(
        select(ClientDocument)
        .where(
            and_(
                ClientDocument.client_id == client_id,
                ClientDocument.tenant_id == tenant_id,
            )
        )
        .order_by(ClientDocument.created_at.desc())
        .limit(20)
    )
    documents = list(docs_result.scalars().all())

    # Documentos que o escritório pediu pelo checklist do mês (o mesmo que o
    # lembrete por e-mail cobra). Só os em aberto: o recebido vira ClientDocument.
    checklist_result = await db.execute(
        select(DocumentChecklistItem)
        .where(
            and_(
                DocumentChecklistItem.client_id == client_id,
                DocumentChecklistItem.tenant_id == tenant_id,
                DocumentChecklistItem.status.in_(_CHECKLIST_OPEN),
            )
        )
        .order_by(DocumentChecklistItem.competence_month.desc())
        .limit(20)
    )
    checklist = list(checklist_result.scalars().all())

    guides_result = await db.execute(
        select(TaxGuide)
        .where(
            and_(
                TaxGuide.client_id == client_id,
                TaxGuide.tenant_id == tenant_id,
            )
        )
        .order_by(TaxGuide.vencimento.desc())
        .limit(20)
    )
    guides = list(guides_result.scalars().all())

    pendencies_result = await db.execute(
        select(DeadlineItem)
        .where(
            and_(
                DeadlineItem.client_id == client_id,
                DeadlineItem.tenant_id == tenant_id,
                DeadlineItem.status == "pending",
            )
        )
        .order_by(DeadlineItem.due_date.asc())
        .limit(20)
    )
    pendencies = list(pendencies_result.scalars().all())

    doc_urls, guide_urls = await _sign_portal_files(tenant_id, documents, guides)

    return {
        "client": {
            "id": str(client.id),
            "name": client.name,
            "document": client.document,
        },
        "closing": (
            {
                "id": str(closing.id),
                "competence": closing.competence,
                "status": closing.status,
                "score": closing.score,
            }
            if closing
            else None
        ),
        "documents": [
            {
                "id": str(c.id),
                "kind": "checklist",
                "name": c.document_name,
                # "pending" do checklist = documento pedido e ainda não enviado.
                "status": "missing" if c.status == "pending" else c.status,
                "requested_at": c.created_at.isoformat() if c.created_at else None,
                "competence": c.competence_month.isoformat()[:7] if c.competence_month else None,
                "notes": c.notes,
                "file_url": None,
                "can_upload": True,
            }
            for c in checklist
        ]
        + [
            {
                "id": str(d.id),
                "kind": "document",
                "name": d.name,
                "status": d.status,
                "requested_at": d.created_at.isoformat() if d.created_at else None,
                "competence": None,
                "notes": d.notes,
                "file_url": doc_urls.get(i),
                "can_upload": d.status in _DOCUMENT_REQUESTED,
            }
            for i, d in enumerate(documents)
        ],
        "guides": [
            {
                "id": str(g.id),
                "type": g.tipo,
                "competence": g.competencia.isoformat() if g.competencia else None,
                "value": float(g.valor) if g.valor is not None else 0.0,
                "due": g.vencimento.isoformat() if g.vencimento else None,
                "status": g.status,
                "pdf_url": guide_urls.get(g.pdf_storage_path) if g.pdf_storage_path else None,
            }
            for g in guides
        ],
        "pendencies": [
            {
                "id": str(p.id),
                "title": p.title,
                "deadline": p.due_date.isoformat() if p.due_date else None,
                "status": p.status,
            }
            for p in pendencies
        ],
    }


@router.get("/preview/{client_id}")
async def get_portal_preview(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated portal view for one client, as office staff sees it.

    Powers the internal /portal page ("Modo preview"): client identity, latest
    monthly closing, requested documents, tax guides and open pendencies.
    CLIENT-role users must use /portal/my-overview instead.
    """
    if current_user.role == UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Use /portal/my-overview for client accounts",
        )

    result = await db.execute(
        select(AccountingClient).where(
            and_(
                AccountingClient.id == client_id,
                AccountingClient.tenant_id == current_user.tenant_id,
            )
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    return await _portal_payload(db, current_user.tenant_id, client)


@router.get("/my-overview")
async def get_my_overview(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Portal do cliente final: o mesmo agregado do preview, só do próprio cliente.

    Não recebe client_id: o cliente é resolvido pelo portal_user_id do usuário
    logado, então não há como pedir dados de outro cliente do escritório.
    """
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only for client users",
        )

    result = await db.execute(
        select(AccountingClient).where(
            and_(
                AccountingClient.portal_user_id == current_user.id,
                AccountingClient.tenant_id == current_user.tenant_id,
            )
        )
    )
    client = result.scalar_one_or_none()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No client data found for this user",
        )

    return await _portal_payload(db, current_user.tenant_id, client)


async def _my_client(db: AsyncSession, current_user: User) -> AccountingClient:
    """Cliente do escritório ligado ao usuário CLIENT logado (ou 403/404)."""
    if current_user.role != UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This endpoint is only for client users",
        )
    client = (
        await db.execute(
            select(AccountingClient).where(
                and_(
                    AccountingClient.portal_user_id == current_user.id,
                    AccountingClient.tenant_id == current_user.tenant_id,
                )
            )
        )
    ).scalar_one_or_none()
    if not client:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No client data found for this user",
        )
    return client


@router.post("/my-documents", status_code=status.HTTP_201_CREATED, summary="Cliente envia um documento")
async def upload_my_document(
    request: Request,
    file: UploadFile = File(...),
    request_id: Optional[uuid.UUID] = Form(None),
    kind: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """O cliente final manda o arquivo de um pedido do escritório (ou um avulso).

    - kind="checklist" + request_id: item do checklist do mês → vira "received"
      e o arquivo entra como documento "review" para o escritório conferir;
    - kind="document" + request_id: documento "missing"/"expired" recebe o
      arquivo e passa a "review";
    - sem request_id: documento novo, "review".
    Tudo filtrado pelo cliente do usuário logado: não há como gravar em outro.
    """
    from app.core import storage as _storage
    from app.core.document_links import DOCUMENTS_BUCKET, storage_ref
    from app.api.v1.endpoints.operations import _DOC_UPLOAD_EXTS, _DOC_UPLOAD_MAX_BYTES
    from app.models.operations import ClientDocument
    from app.models.obligation import DocumentChecklistItem
    from app.services.audit import log_audit_event

    client = await _my_client(db, current_user)
    tenant_id = current_user.tenant_id

    if request_id is not None and kind not in ("checklist", "document"):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "kind deve ser 'checklist' ou 'document'")

    checklist_item = None
    target_doc = None
    if request_id is not None and kind == "checklist":
        checklist_item = (
            await db.execute(
                select(DocumentChecklistItem).where(
                    and_(
                        DocumentChecklistItem.id == request_id,
                        DocumentChecklistItem.client_id == client.id,
                        DocumentChecklistItem.tenant_id == tenant_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if not checklist_item:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido de documento não encontrado")
        if checklist_item.status not in _CHECKLIST_OPEN:
            raise HTTPException(status.HTTP_409_CONFLICT, "Este documento já foi enviado")
    elif request_id is not None:
        target_doc = (
            await db.execute(
                select(ClientDocument).where(
                    and_(
                        ClientDocument.id == request_id,
                        ClientDocument.client_id == client.id,
                        ClientDocument.tenant_id == tenant_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if not target_doc:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Pedido de documento não encontrado")
        if target_doc.status not in _DOCUMENT_REQUESTED:
            raise HTTPException(status.HTTP_409_CONFLICT, "Este documento já foi enviado")

    # Documento novo (não é a resposta a um pedido já cadastrado) conta no
    # limite de documentos por cliente do plano do escritório.
    if target_doc is None:
        await ensure_can_add_document(db, tenant_id, client.id)

    file_ext = ""
    if file.filename and "." in file.filename:
        file_ext = "." + file.filename.rsplit(".", 1)[-1].lower()
    if file_ext not in _DOC_UPLOAD_EXTS:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Tipo de arquivo não aceito. Use: {', '.join(sorted(_DOC_UPLOAD_EXTS))}",
        )
    content = await file.read(_DOC_UPLOAD_MAX_BYTES + 1)
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Arquivo vazio")
    if len(content) > _DOC_UPLOAD_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Arquivo maior que {_DOC_UPLOAD_MAX_BYTES // (1024 * 1024)} MB",
        )

    storage_path = f"{tenant_id}/{uuid.uuid4().hex}{file_ext}"
    try:
        await _storage.upload_bytes(
            DOCUMENTS_BUCKET, storage_path, content, file.content_type or "application/octet-stream"
        )
    except Exception:  # noqa: BLE001
        logger.exception("Portal: upload do cliente falhou (%s)", storage_path)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Não foi possível guardar o arquivo agora. Tente novamente em instantes.",
        )
    file_url = storage_ref(storage_path)
    original_name = (file.filename or "Documento").strip()[:255] or "Documento"

    if target_doc is not None:
        document = target_doc
        document.file_url = file_url
        document.status = "review"
        document.updated_at = _now()
    else:
        name = checklist_item.document_name[:255] if checklist_item is not None else original_name
        document = ClientDocument(
            tenant_id=tenant_id,
            client_id=client.id,
            name=name if len(name) >= 2 else f"Documento {name}",
            document_type="Portal do cliente",
            status="review",
            file_url=file_url,
            parse_status="pending",
            notes=f"Enviado pelo cliente no portal ({original_name})",
        )
    if checklist_item is not None:
        checklist_item.status = "received"
        checklist_item.received_at = _now()
        db.add(checklist_item)
    db.add(document)
    await db.commit()
    await db.refresh(document)

    await log_audit_event(
        db=db,
        tenant_id=tenant_id,
        actor_user_id=current_user.id,
        actor_role=current_user.role.value,
        action="portal.document.upload",
        entity_type="document",
        entity_id=document.id,
        after_data={"name": document.name, "request_id": str(request_id) if request_id else None, "kind": kind},
        ip_address=get_client_ip(request),
        user_agent=request.headers.get("User-Agent"),
    )

    return {"id": str(document.id), "name": document.name, "status": document.status}


# ---------------------------------------------------------------------------
# Magic Link Authentication
# ---------------------------------------------------------------------------

class MagicLinkRequestSchema(BaseModel):
    """Pedido do escritório: link de acesso ao portal para um cliente.

    Com client_id ("Dar acesso ao portal"): garante o usuário CLIENT do cliente
    (cria sem senha utilizável, ou vincula um existente) e envia o link.
    Sem client_id: exige um usuário CLIENT já existente com esse e-mail.
    """
    email: Optional[EmailStr] = None
    client_id: Optional[uuid.UUID] = None


class MagicLinkSelfRequestSchema(BaseModel):
    """Pedido público do cliente final na tela de login do portal."""
    email: EmailStr


class MagicLinkVerifySchema(BaseModel):
    """Verify a magic link token."""
    token: str


_MAGIC_LINK_SUBJECT = "Seu link de acesso ao portal do cliente"
_SELF_REQUEST_MESSAGE = "Se o e-mail estiver cadastrado, você receberá o link de acesso em instantes."
_EMAIL_NOT_CONFIGURED = (
    "Envio de e-mail não configurado neste ambiente. "
    "Peça o link de acesso diretamente ao seu escritório contábil."
)


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash of the raw token for safe storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


async def _issue_magic_token(
    db: AsyncSession, client_user: User, ip: Optional[str]
) -> tuple[str, PortalMagicToken]:
    """Invalida os links abertos do usuário e cria um novo (sem commit).

    Devolve o link com o token cru; no banco fica só o hash.
    """
    raw_token = secrets.token_urlsafe(32)
    existing = await db.execute(
        select(PortalMagicToken).where(
            and_(PortalMagicToken.user_id == client_user.id, PortalMagicToken.used == False)  # noqa: E712
        )
    )
    for old_token in existing.scalars().all():
        old_token.used = True

    magic = PortalMagicToken(
        tenant_id=client_user.tenant_id,
        user_id=client_user.id,
        token_hash=_hash_token(raw_token),
        email=client_user.email,
        # Explícito: o model só tem server_default, que o SQLite lê como texto truthy.
        used=False,
        expires_at=_now() + timedelta(hours=24),
        ip_address=ip,
    )
    db.add(magic)
    return f"{settings.portal_url}/login?token={raw_token}", magic


async def _ensure_portal_user(
    db: AsyncSession, tenant_id: uuid.UUID, client: AccountingClient, email: Optional[str]
) -> User:
    """Garante o usuário CLIENT ligado ao cliente (sem commit).

    Usuário novo recebe senha aleatória descartada: o acesso é só por link mágico.
    """
    from app.core.security import get_password_hash

    if client.portal_user_id:
        user = (
            await db.execute(
                select(User).where(and_(User.id == client.portal_user_id, User.tenant_id == tenant_id))
            )
        ).scalar_one_or_none()
        if user:
            if user.role != UserRole.CLIENT:
                raise HTTPException(status.HTTP_409_CONFLICT, "Vínculo de portal inválido para este cliente")
            if not user.is_active:
                raise HTTPException(status.HTTP_409_CONFLICT, "O acesso deste cliente ao portal está desativado")
            if email and email.lower() != user.email.lower():
                # O escritório corrigiu o e-mail do cliente (ex.: digitado errado
                # no cadastro): o acesso ao portal passa para o e-mail novo. Os
                # links abertos do e-mail antigo caem em _issue_magic_token.
                outro = (
                    await db.execute(
                        select(User.id).where(
                            and_(
                                User.tenant_id == tenant_id,
                                func.lower(User.email) == email.lower(),
                                User.id != user.id,
                            )
                        )
                    )
                ).first()
                if outro:
                    raise HTTPException(
                        status.HTTP_409_CONFLICT,
                        "Este e-mail já é usado por outro acesso deste escritório",
                    )
                logger.info(
                    "E-mail do portal trocado: cliente=%s de %s para %s", client.id, user.email, email
                )
                user.email = email
                user.updated_at = _now()
                db.add(user)
            return user

    if not email:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Informe o e-mail do cliente para dar acesso ao portal",
        )

    user = (
        await db.execute(
            select(User).where(and_(User.tenant_id == tenant_id, func.lower(User.email) == email.lower()))
        )
    ).scalar_one_or_none()
    if user:
        if user.role != UserRole.CLIENT:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Este e-mail pertence a um usuário da equipe do escritório",
            )
        if not user.is_active:
            raise HTTPException(status.HTTP_409_CONFLICT, "O acesso deste e-mail ao portal está desativado")
        other = (
            await db.execute(
                select(AccountingClient.id).where(
                    and_(
                        AccountingClient.portal_user_id == user.id,
                        AccountingClient.tenant_id == tenant_id,
                        AccountingClient.id != client.id,
                    )
                )
            )
        ).first()
        if other:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Este e-mail já dá acesso ao portal de outro cliente",
            )
    else:
        user = User(
            tenant_id=tenant_id,
            email=email,
            hashed_password=get_password_hash(secrets.token_urlsafe(32)),
            full_name=client.name,
            role=UserRole.CLIENT,
            is_active=True,
        )
        db.add(user)
        await db.flush()

    client.portal_user_id = user.id
    client.updated_at = _now()
    db.add(client)
    return user


@router.post("/magic-link/request", summary="Escritório envia link de acesso ao portal")
async def request_magic_link(
    body: MagicLinkRequestSchema,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Gera um link de uso único (24 h) e o envia por e-mail ao cliente.

    Resposta: {sent, delivery, email, expires_at, reason?, portal_link?}.
    O link só volta no JSON quando o envio de e-mail não está configurado
    (delivery="manual"), para o escritório copiar e repassar.
    """
    if not current_user.is_admin_or_owner():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can issue magic links",
        )
    await ensure_feature(db, current_user.tenant_id, FEATURE_PORTAL_CLIENTE, current_user.email)
    if body.client_id is None and body.email is None:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, "Informe client_id ou email")

    if body.client_id is not None:
        client = (
            await db.execute(
                select(AccountingClient).where(
                    and_(
                        AccountingClient.id == body.client_id,
                        AccountingClient.tenant_id == current_user.tenant_id,
                    )
                )
            )
        ).scalar_one_or_none()
        if not client:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")
        client_user = await _ensure_portal_user(
            db, current_user.tenant_id, client, body.email or client.email
        )
    else:
        client_user = (
            await db.execute(
                select(User).where(
                    and_(
                        func.lower(User.email) == str(body.email).lower(),
                        User.tenant_id == current_user.tenant_id,
                        User.role == UserRole.CLIENT,
                        User.is_active == True,  # noqa: E712
                    )
                )
            )
        ).scalar_one_or_none()
        if not client_user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Nenhum usuário ativo do portal com este e-mail",
            )

    portal_link, magic = await _issue_magic_token(db, client_user, get_client_ip(request))
    await db.commit()

    response: dict = {
        "email": client_user.email,
        "expires_at": magic.expires_at.isoformat(),
    }

    if not email_service.is_configured():
        logger.info(
            "Magic link emitido em modo manual (e-mail não configurado) para %s por %s",
            client_user.email, current_user.email,
        )
        return {
            **response,
            "sent": False,
            "delivery": "manual",
            "reason": "Envio de e-mail não configurado. Copie o link e envie ao cliente.",
            "portal_link": portal_link,
        }

    sent = await email_service.send_email(
        to=client_user.email,
        subject=_MAGIC_LINK_SUBJECT,
        html=email_service.render_portal_magic_link_email(portal_link),
    )
    if not sent:
        # Ninguém recebeu o link: inutiliza o token em vez de deixá-lo válido.
        magic.used = True
        await db.commit()
        return {
            **response,
            "sent": False,
            "delivery": "email",
            "reason": "O provedor de e-mail recusou o envio. Tente novamente em instantes.",
        }

    logger.info("Magic link enviado por e-mail para %s por %s", client_user.email, current_user.email)
    return {**response, "sent": True, "delivery": "email"}


@router.post("/magic-link/self-request", summary="Cliente pede o próprio link de acesso")
async def self_request_magic_link(
    body: MagicLinkSelfRequestSchema,
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Endpoint público da tela de login do portal.

    Resposta sempre igual (não revela se o e-mail existe). Limites: por IP
    (mesmo teto do login, chave própria) e, em silêncio, por e-mail (evita
    bombardear a caixa de alguém). O envio roda em background para o tempo
    de resposta não denunciar e-mail cadastrado.
    """
    ip = get_client_ip(request)
    rl_key = f"portal-link:{ip}"
    auth_rate_limiter.check_login_ip(rl_key)
    auth_rate_limiter.record_login_failure(rl_key)

    if not email_service.is_configured():
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _EMAIL_NOT_CONFIGURED)

    generic = {"status": "accepted", "message": _SELF_REQUEST_MESSAGE}
    email = str(body.email).lower()

    email_key = f"portal-link:{email}"
    try:
        auth_rate_limiter.check_otp_user(email_key)
    except HTTPException:
        logger.info("Pedido de link do portal ignorado (limite por e-mail)")
        return generic
    auth_rate_limiter.record_otp_failure(email_key)

    users = (
        await db.execute(
            select(User)
            .where(
                and_(
                    func.lower(User.email) == email,
                    User.role == UserRole.CLIENT,
                    User.is_active == True,  # noqa: E712
                )
            )
            .limit(5)
        )
    ).scalars().all()

    links = []
    for user in users:
        link, _ = await _issue_magic_token(db, user, ip)
        links.append((user.email, link))
    if links:
        await db.commit()
    for to, link in links:
        background_tasks.add_task(
            email_service.send_email,
            to=to,
            subject=_MAGIC_LINK_SUBJECT,
            html=email_service.render_portal_magic_link_email(link),
        )
    return generic


@router.post("/magic-link/verify", summary="Verify magic link token and get JWT")
async def verify_magic_link(
    body: MagicLinkVerifySchema,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Exchange a magic link token for a JWT access token.

    This is a public endpoint (no auth required).
    The client receives this token via the link emailed by their accounting office.
    """
    token_hash = _hash_token(body.token)

    result = await db.execute(
        select(PortalMagicToken).where(PortalMagicToken.token_hash == token_hash)
    )
    magic = result.scalar_one_or_none()

    if not magic:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    now = datetime.now(timezone.utc)

    if magic.used:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Este link já foi utilizado. Peça um novo link na página de acesso do portal.",
        )

    if now > _as_utc(magic.expires_at):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Link expirado. Peça um novo link na página de acesso do portal.",
        )

    # Fetch the associated user
    user_result = await db.execute(select(User).where(User.id == magic.user_id))
    user = user_result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Conta de portal inativa. Entre em contato com o escritório.",
        )

    # Mark token as used
    magic.used = True
    magic.used_at = now
    await db.commit()

    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value,
    )

    logger.info(
        "Magic link verified and JWT issued for client user %s (tenant %s)",
        user.email, user.tenant_id,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "email": user.email,
        "tenant_id": str(user.tenant_id),
    }
