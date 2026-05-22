"""
Authentication Endpoints for FiscWise

Handles user authentication, login, and token generation.
"""

import os
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from pydantic import BaseModel, Field
from typing import Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deps import get_db, get_current_user
from app.core.security import verify_password, create_access_token, get_password_hash
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.schemas.token import AuthResponse, UserInfo

logger = logging.getLogger(__name__)


router = APIRouter()


@router.post("/login", response_model=AuthResponse, summary="User Login")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """
    OAuth2 compatible token login endpoint.

    Authenticates a user with email (as username) and password.
    Returns a JWT access token on successful authentication.

    Enforces tenant isolation: if multiple users with the same email exist
    across different tenants (should not happen due to onboarding flow),
    rejects the request with 401 to prevent cross-tenant leakage.

    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session dependency

    Returns:
        Token: JWT access token and token type

    Raises:
        HTTPException: 401 if credentials are invalid, user is inactive, or multi-tenant collision
    """
    # Query all users with this email (should be max 1 per tenant isolation constraint)
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    users = result.scalars().all()

    # Security: If multiple users found, it indicates a data integrity issue or
    # an attack attempt. Reject with 401 to avoid revealing tenant information.
    if len(users) != 1:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = users[0]

    # Validate password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Validate user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    
    # Create access token with user information
    access_token = create_access_token(
        user_id=str(user.id),
        tenant_id=str(user.tenant_id),
        role=user.role.value
    )
    
    return AuthResponse(
        access_token=access_token,
        token_type="bearer",
        tenant_id=str(user.tenant_id),
        user=UserInfo(
            id=str(user.id),
            email=user.email,
            full_name=getattr(user, "full_name", None),
            role=user.role.value,
        ),
    )


class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token (JWT)


@router.post("/google", response_model=AuthResponse, summary="Google OAuth Login / Register")
async def google_auth(
    body: GoogleAuthRequest,
    db: AsyncSession = Depends(get_db),
) -> AuthResponse:
    """
    Authenticate or register a user via Google OAuth.

    Receives the Google ID token from the frontend, verifies it with Google's
    public keys, and either logs in an existing user or creates a new tenant +
    owner user for first-time sign-ins.

    Args:
        body: Request body containing the Google credential (ID token)
        db: Database session

    Returns:
        AuthResponse with JWT access token and user info

    Raises:
        HTTPException 400: If GOOGLE_CLIENT_ID is not configured
        HTTPException 401: If the Google token is invalid
        HTTPException 500: If account creation fails
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Google OAuth is not configured on this server",
        )

    # Verify Google ID token
    try:
        id_info = google_id_token.verify_oauth2_token(
            body.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
            clock_skew_in_seconds=10,
        )
    except ValueError as exc:
        logger.warning("Invalid Google token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token Google inválido ou expirado",
        )

    google_email: str = id_info.get("email", "").lower().strip()
    google_name: str = id_info.get("name", "")

    if not google_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Não foi possível obter o e-mail da conta Google",
        )

    # Look up existing user by email
    result = await db.execute(select(User).where(User.email == google_email))
    existing_user = result.scalar_one_or_none()

    if existing_user:
        # Existing user — just log in
        if not existing_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Conta inativa. Entre em contato com o suporte.",
            )
        access_token = create_access_token(
            user_id=str(existing_user.id),
            tenant_id=str(existing_user.tenant_id),
            role=existing_user.role.value,
        )
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            tenant_id=str(existing_user.tenant_id),
            user=UserInfo(
                id=str(existing_user.id),
                email=existing_user.email,
                full_name=existing_user.full_name,
                role=existing_user.role.value,
            ),
        )

    # New user — create tenant + owner in a single transaction
    try:
        new_tenant = Tenant(
            name=google_name or google_email.split("@")[0],
            subscription_status=SubscriptionStatus.TRIAL,
        )
        db.add(new_tenant)
        await db.flush()  # get tenant.id without committing

        # Google users get a random unusable password
        random_password = get_password_hash(os.urandom(32).hex())

        new_user = User(
            tenant_id=new_tenant.id,
            email=google_email,
            hashed_password=random_password,
            full_name=google_name,
            role=UserRole.OWNER,
            is_active=True,
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_tenant)
        await db.refresh(new_user)

        access_token = create_access_token(
            user_id=str(new_user.id),
            tenant_id=str(new_tenant.id),
            role=new_user.role.value,
        )
        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            tenant_id=str(new_tenant.id),
            user=UserInfo(
                id=str(new_user.id),
                email=new_user.email,
                full_name=new_user.full_name,
                role=new_user.role.value,
            ),
        )
    except Exception as exc:
        await db.rollback()
        logger.error("Failed to create Google OAuth user: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao criar conta. Tente novamente.",
        )


@router.post("/logout", summary="User Logout")
async def logout():
    """
    Logout endpoint (placeholder for token invalidation).
    
    In a stateless JWT implementation, logout is typically handled client-side
    by removing the token. For enhanced security, implement token blacklisting
    using Redis or a similar cache.
    
    Returns:
        dict: Success message
    """
    return {
        "message": "Successfully logged out",
        "detail": "Remove the access token from client storage"
    }


@router.get("/me", summary="Get Current User Info")
async def get_me(
    current_user: User = Depends(get_current_user)
):
    """
    Get current authenticated user information.

    Protected endpoint that requires valid JWT token.
    Returns user profile information.

    Args:
        current_user: Current authenticated user from token

    Returns:
        dict: User profile information
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "role": current_user.role.value,
        "tenant_id": str(current_user.tenant_id),
        "is_active": current_user.is_active,
        "created_at": current_user.created_at.isoformat(),
    }


@router.get("/tenant", summary="Get Current Tenant Info")
async def get_tenant(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "document": tenant.document,
        "plan_slug": getattr(tenant, "plan_slug", None),
        "phone": getattr(tenant, "phone", None),
        "address": getattr(tenant, "address", None),
        "website": getattr(tenant, "website", None),
        "subscription_status": tenant.subscription_status.value,
        "created_at": tenant.created_at.isoformat(),
    }


class UpdateProfileRequest(BaseModel):
    full_name: Optional[str] = Field(None, min_length=2, max_length=255)
    phone: Optional[str] = Field(None, max_length=20)


@router.patch("/me", summary="Update User Profile")
async def update_me(
    body: UpdateProfileRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if body.full_name is not None:
        current_user.full_name = body.full_name
    if body.phone is not None:
        current_user.phone = body.phone
    await db.commit()
    await db.refresh(current_user)
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "phone": getattr(current_user, "phone", None),
        "role": current_user.role.value,
    }


class UpdateTenantRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    document: Optional[str] = Field(None, max_length=32)
    plan_slug: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    address: Optional[str] = Field(None, max_length=500)
    website: Optional[str] = Field(None, max_length=255)


@router.patch("/tenant", summary="Update Tenant")
async def update_tenant(
    body: UpdateTenantRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Tenant).where(Tenant.id == current_user.tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    if body.name is not None:
        tenant.name = body.name
    if body.document is not None:
        tenant.document = body.document
    if body.plan_slug is not None:
        tenant.plan_slug = body.plan_slug
    if body.phone is not None:
        tenant.phone = body.phone
    if body.address is not None:
        tenant.address = body.address
    if body.website is not None:
        tenant.website = body.website
    await db.commit()
    await db.refresh(tenant)
    return {
        "id": str(tenant.id),
        "name": tenant.name,
        "document": tenant.document,
        "plan_slug": getattr(tenant, "plan_slug", None),
        "phone": getattr(tenant, "phone", None),
        "address": getattr(tenant, "address", None),
        "website": getattr(tenant, "website", None),
        "subscription_status": tenant.subscription_status.value,
    }


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


@router.post("/change-password", summary="Change Password")
async def change_password(
    body: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    if not verify_password(body.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Senha atual incorreta")
    current_user.hashed_password = get_password_hash(body.new_password)
    await db.commit()
    return {"message": "Senha alterada com sucesso"}
