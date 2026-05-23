"""
Onboarding Endpoints for FiscWise

Handles public tenant registration and onboarding flow.
Creates tenant and owner user in a single atomic transaction.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db
from app.core.security import get_password_hash, create_access_token
from app.models.tenant import Tenant, SubscriptionStatus
from app.models.user import User, UserRole
from app.schemas.onboarding import TenantRegistrationRequest
from app.schemas.token import AuthResponse, UserInfo


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/register", response_model=AuthResponse, summary="Register New Tenant")
async def register_tenant(
    registration: TenantRegistrationRequest,
    db: AsyncSession = Depends(get_db)
) -> AuthResponse:
    """
    Public endpoint for tenant registration (onboarding).
    
    Creates a new tenant (company) and its owner user in a single atomic transaction.
    This is the entry point for new customers signing up for the platform.
    
    Process:
    1. Validates that email is not already registered
    2. Creates Tenant record with TRIAL subscription status
    3. Creates Owner User record linked to the tenant
    4. Commits both in a single transaction (atomic operation)
    
    Args:
        registration: Tenant registration data (company info + owner credentials)
        db: Database session dependency
        
    Returns:
        TenantRegistrationResponse: Success message with tenant_id and user_id
        
    Raises:
        HTTPException: 400 if email is already registered
        HTTPException: 500 if database transaction fails
    """
    
    # Step 1: Check if email is already registered
    existing_user_query = await db.execute(
        select(User).where(User.email == registration.owner_email)
    )
    existing_user = existing_user_query.scalar_one_or_none()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Email '{registration.owner_email}' is already registered",
            headers={"X-Error-Code": "EMAIL_ALREADY_EXISTS"}
        )
    
    try:
        # Step 2: Create Tenant instance
        new_tenant = Tenant(
            name=registration.company_name,
            document=registration.document,
            subscription_status=SubscriptionStatus.TRIAL,
            plan_slug="free",
        )
        
        db.add(new_tenant)
        
        # Flush to generate tenant.id without committing the transaction
        await db.flush()
        
        # Step 3: Hash the owner password
        hashed_password = get_password_hash(registration.owner_password)
        
        # Step 4: Create Owner User instance linked to the new tenant
        new_owner = User(
            tenant_id=new_tenant.id,
            email=registration.owner_email,
            hashed_password=hashed_password,
            full_name=registration.owner_full_name,
            phone=registration.owner_phone,
            role=UserRole.OWNER,
            is_active=True
        )
        
        db.add(new_owner)
        
        # Step 5: Commit the atomic transaction (both tenant and user)
        await db.commit()
        
        # Step 6: Refresh instances to get all database-generated fields
        await db.refresh(new_tenant)
        await db.refresh(new_owner)
        
        # Step 7: Generate access token and return AuthResponse
        access_token = create_access_token(
            user_id=str(new_owner.id),
            tenant_id=str(new_tenant.id),
            role=new_owner.role.value,
        )

        return AuthResponse(
            access_token=access_token,
            token_type="bearer",
            tenant_id=str(new_tenant.id),
            user=UserInfo(
                id=str(new_owner.id),
                email=new_owner.email,
                full_name=registration.owner_full_name,
                phone=registration.owner_phone,
                role=new_owner.role.value,
            ),
        )
        
    except IntegrityError:
        await db.rollback()
        logger.warning("Tenant registration failed due to integrity constraint", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration data conflicts with an existing record.",
            headers={"X-Error-Code": "REGISTRATION_CONFLICT"}
        )
    except Exception:
        # Rollback transaction on any error
        await db.rollback()
        
        # Log the error (internal only, do not expose to client)
        logger.error("Tenant registration failed", exc_info=True)
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create tenant and owner user. Please try again.",
            headers={"X-Error-Code": "REGISTRATION_FAILED"}
        )


@router.get("/health", summary="Onboarding Health Check")
async def onboarding_health():
    """
    Health check endpoint for onboarding service.
    
    Returns:
        dict: Status message
    """
    return {
        "status": "Onboarding service operational",
        "endpoint": "/api/v1/onboarding/register"
    }
