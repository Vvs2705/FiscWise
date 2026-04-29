"""
Authentication Endpoints for ContaFlow

Handles user authentication, login, and token generation.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_db, get_current_user
from app.core.security import verify_password, create_access_token
from app.models.user import User
from app.schemas.token import AuthResponse, UserInfo


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
    
    Args:
        form_data: OAuth2 form with username (email) and password
        db: Database session dependency
        
    Returns:
        Token: JWT access token and token type
        
    Raises:
        HTTPException: 401 if credentials are invalid or user is inactive
    """
    # Query user by email (form_data.username contains the email)
    result = await db.execute(
        select(User).where(User.email == form_data.username)
    )
    user = result.scalar_one_or_none()
    
    # Validate user exists
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
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
