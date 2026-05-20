"""
Security Module for ContaFlow

Handles password hashing, verification, and JWT token generation.
Uses bcrypt directly for password hashing (bcrypt 4.x+ compatible)
and python-jose for JWT tokens.

Note: passlib 1.7.x is incompatible with bcrypt >= 4.0 because it reads
bcrypt.__about__.__version__ which was removed in bcrypt 4.0.  We call the
bcrypt library directly instead of going through passlib to avoid this.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
from jose import jwt

# JWT Configuration - Import from config for consistency
from app.core.config import settings

JWT_SECRET_KEY = settings.JWT_SECRET_KEY
JWT_ALGORITHM = settings.JWT_ALGORITHM
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a bcrypt-hashed password.

    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password from database

    Returns:
        bool: True if password matches, False otherwise
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.

    Bcrypt has a maximum input length of 72 bytes; passwords longer than
    that are silently truncated by the underlying C library.  We reject
    them explicitly so callers get a clear error instead of silent data loss.

    Args:
        password: The plain text password to hash

    Returns:
        str: The bcrypt hashed password (60-char string starting with $2b$)

    Raises:
        ValueError: If the password exceeds 72 bytes.
    """
    encoded = password.encode("utf-8")
    if len(encoded) > 72:
        raise ValueError("Password must be at most 72 bytes.")

    hashed = bcrypt.hashpw(encoded, bcrypt.gensalt())
    return hashed.decode("utf-8")


def create_access_token(user_id: str, tenant_id: str, role: str) -> str:
    """
    Create a JWT access token for authentication.
    
    Args:
        user_id: The user's UUID as string
        tenant_id: The tenant's UUID as string
        role: The user's role (owner/admin/member)
        
    Returns:
        str: The encoded JWT token
    """
    # Calculate expiration time
    issued_at = datetime.now(timezone.utc)
    expire = issued_at + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Create JWT payload
    payload = {
        "sub": user_id,  # Subject (user ID)
        "tenant_id": tenant_id,  # Tenant ID for multi-tenancy
        "role": role,  # User role for RBAC
        "exp": expire,  # Expiration time
        "iat": issued_at,  # Issued at time
    }
    
    # Encode and return JWT token
    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt
