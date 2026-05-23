"""Client Portal Endpoints for FiscWise

Handles client portal invitations and access management.
"""

import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.models.user import User, UserRole
from app.models.operations import ClientPortalInvite, InviteStatus, AccountingClient
from app.core.security import create_access_token

router = APIRouter(prefix="/portal", tags=["Client Portal"])


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
