"""
Security Module for ContaFlow

Handles password hashing, verification, and JWT token generation.
Uses bcrypt for password hashing and python-jose for JWT tokens.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from jose import jwt
from passlib.context import CryptContext


# Password hashing context using bcrypt
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# JWT Configuration
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-here-generate-with-openssl-rand-hex-64")
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "30"))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password from database
        
    Returns:
        bool: True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Bcrypt has a maximum password length of 72 bytes.
    This function truncates passwords longer than 72 bytes to comply with bcrypt limits.
    
    Args:
        password: The plain text password to hash
        
    Returns:
        str: The bcrypt hashed password
    """
    # Truncate password to 72 characters (safe limit for bcrypt)
    if len(password) > 72:
        password = password[:72]
    
    return pwd_context.hash(password)


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
    expire = datetime.utcnow() + timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    
    # Create JWT payload
    payload = {
        "sub": user_id,  # Subject (user ID)
        "tenant_id": tenant_id,  # Tenant ID for multi-tenancy
        "role": role,  # User role for RBAC
        "exp": expire,  # Expiration time
        "iat": datetime.utcnow(),  # Issued at time
    }
    
    # Encode and return JWT token
    encoded_jwt = jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return encoded_jwt
