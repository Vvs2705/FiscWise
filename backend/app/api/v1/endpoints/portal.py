"""Client Portal Endpoints for FiscWise

Handles client portal invitations, magic link authentication, and client data.
"""

import hashlib
import logging
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request, status
from pydantic import AliasChoices, BaseModel, EmailStr, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
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


async def _portal_payload(db: AsyncSession, tenant_id: uuid.UUID, client: AccountingClient) -> dict:
    """Agrega o que o portal mostra de UM cliente.

    Toda consulta filtra por client.id E tenant_id: quem chama já resolveu
    `client` dentro do escritório certo, e aqui nada vaza de outro cliente.
    """
    from app.models.operations import ClientDocument, DeadlineItem
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
                "id": str(d.id),
                "name": d.name,
                "status": d.status,
                "requested_at": d.created_at.isoformat() if d.created_at else None,
            }
            for d in documents
        ],
        "guides": [
            {
                "id": str(g.id),
                "type": g.tipo,
                "competence": g.competencia.isoformat() if g.competencia else None,
                "value": float(g.valor) if g.valor is not None else 0.0,
                "due": g.vencimento.isoformat() if g.vencimento else None,
                "status": g.status,
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
                raise HTTPException(
                    status.HTTP_409_CONFLICT,
                    f"Este cliente já acessa o portal com o e-mail {user.email}",
                )
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
