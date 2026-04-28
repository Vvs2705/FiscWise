"""
Token Schemas for ContaFlow

Pydantic models for JWT token request/response and payload validation.
"""

from pydantic import BaseModel


class Token(BaseModel):
    """
    JWT Token response schema.
    
    Returned after successful authentication.
    """
    access_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """
    JWT Token payload schema.
    
    Represents the decoded JWT token data.
    Used for validating and extracting token claims.
    """
    sub: str  # Subject (user_id)
    tenant_id: str  # Tenant ID for multi-tenancy
    role: str  # User role (owner/admin/member)
