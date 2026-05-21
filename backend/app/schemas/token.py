"""
Token Schemas for FiscWise

Pydantic models for JWT token request/response and payload validation.
"""

from pydantic import BaseModel
from typing import Optional


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserInfo(BaseModel):
    id: str
    email: str
    full_name: Optional[str] = None
    role: str


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user: UserInfo


class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role: str
