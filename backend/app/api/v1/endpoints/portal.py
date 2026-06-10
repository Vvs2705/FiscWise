"""Client Portal Endpoints for FiscWise

Handles client portal invitations, magic link authentication, and client data.
"""

import hashlib
import logging
import os
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.portal import PortalMagicToken
from app.models.user import User, UserRole
from app.models.operations import ClientPortalInvite, InviteStatus, AccountingClient
from app.core.security import create_access_token

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/portal", tags=["Client Portal"])

# Frontend portal URL — override via PORTAL_URL env var in production
_PORTAL_URL = os.getenv("PORTAL_URL", "https://fiscwise.com.br/portal")


class InviteClientRequest(BaseModel):
    """Request to invite a client to the portal."""
    client_id: uuid.UUID
    email: EmailStr = Field(..., description="Client contact email")


class InviteClientResponse(BaseModel):
    """Response after inviting a client."""
    invite_id: uuid.UUID
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
        expires_at=datetime.utcnow() + timedelta(days=30)
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
    if invite.expires_at and datetime.utcnow() > invite.expires_at:
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

    if invite.expires_at and datetime.utcnow() > invite.expires_at:
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

    # Update client with portal_user_id
    client = await db.get(AccountingClient, invite.client_id)
    client.portal_user_id = client_user.id

    # Mark invitation as accepted
    invite.status = InviteStatus.ACCEPTED
    invite.accepted_at = datetime.utcnow()

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


@router.get("/preview/{client_id}")
async def get_portal_preview(
    client_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Aggregated portal view for one client, as office staff sees it.

    Powers the internal /portal page ("Modo preview"): client identity, latest
    monthly closing, requested documents, tax guides and open pendencies.
    CLIENT-role users must use /portal/my-data instead.
    """
    from app.models.operations import ClientDocument, DeadlineItem
    from app.domain.guias.models import TaxGuide
    from app.domain.monthly_closing.models import MonthlyClosing

    if current_user.role == UserRole.CLIENT:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Use /portal/my-data for client accounts",
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

    closing_result = await db.execute(
        select(MonthlyClosing)
        .where(
            and_(
                MonthlyClosing.client_id == client_id,
                MonthlyClosing.tenant_id == current_user.tenant_id,
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
                ClientDocument.tenant_id == current_user.tenant_id,
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
                TaxGuide.tenant_id == current_user.tenant_id,
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
                DeadlineItem.tenant_id == current_user.tenant_id,
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


# ---------------------------------------------------------------------------
# Magic Link Authentication
# ---------------------------------------------------------------------------

class MagicLinkRequestSchema(BaseModel):
    """Request a magic link for a client portal user."""
    email: EmailStr


class MagicLinkVerifySchema(BaseModel):
    """Verify a magic link token."""
    token: str


def _hash_token(raw_token: str) -> str:
    """SHA-256 hash of the raw token for safe storage."""
    return hashlib.sha256(raw_token.encode()).hexdigest()


@router.post("/magic-link/request", summary="Request magic link for portal login")
async def request_magic_link(
    body: MagicLinkRequestSchema,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Generate a one-time magic link for a client portal user.

    The office staff calls this endpoint to send a login link to a client.
    The link is valid for 24 hours and can only be used once.

    NOTE: In production, the link should be emailed to the client.
    Currently returns the link in the response for integration/testing.
    When an email provider (Resend/SendGrid) is configured, the link will
    be sent automatically and the response will only confirm the request.
    """
    if current_user.role.value not in ("owner", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners and admins can issue magic links",
        )

    # Find the CLIENT user with this email in this tenant
    user_result = await db.execute(
        select(User).where(
            and_(
                User.email == body.email,
                User.tenant_id == current_user.tenant_id,
                User.role == UserRole.CLIENT,
                User.is_active == True,
            )
        )
    )
    client_user = user_result.scalar_one_or_none()
    if not client_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active client portal user found with email '{body.email}'",
        )

    # Generate a cryptographically secure token (32 bytes = 64 hex chars)
    raw_token = secrets.token_urlsafe(32)
    token_hash = _hash_token(raw_token)

    # Invalidate any existing unused tokens for this user
    existing_result = await db.execute(
        select(PortalMagicToken).where(
            and_(
                PortalMagicToken.user_id == client_user.id,
                PortalMagicToken.used == False,
            )
        )
    )
    for old_token in existing_result.scalars().all():
        old_token.used = True

    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)
    ip = request.client.host if request and request.client else None

    magic_token = PortalMagicToken(
        tenant_id=current_user.tenant_id,
        user_id=client_user.id,
        token_hash=token_hash,
        email=body.email,
        expires_at=expires_at,
        ip_address=ip,
    )
    db.add(magic_token)
    await db.commit()

    portal_link = f"{_PORTAL_URL}/login?token={raw_token}"

    logger.info(
        "Magic link issued for client user %s by %s (tenant %s)",
        body.email, current_user.email, current_user.tenant_id
    )

    # TODO: when email provider is configured, send portal_link to body.email
    # For now, return it in the response so integrators can use it directly.
    return {
        "status": "issued",
        "email": body.email,
        "expires_at": expires_at.isoformat(),
        "portal_link": portal_link,
        "note": "In production, this link will be sent via email. Store it securely.",
    }


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
            detail="Este link já foi utilizado. Solicite um novo link ao seu escritório.",
        )

    if now > magic.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Link expirado. Solicite um novo link ao seu escritório.",
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
