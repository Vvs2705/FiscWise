"""
Onboarding Schemas for ContaFlow

Pydantic models for tenant registration and onboarding flow.
"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional


class TenantRegistrationRequest(BaseModel):
    """
    Schema for tenant registration request.
    
    Used for public onboarding endpoint where a new company
    and its owner user are created in a single atomic transaction.
    
    Attributes:
        company_name: Name of the company/tenant
        document: Company document (CNPJ/CPF) - optional
        owner_email: Email of the owner user (validated with EmailStr)
        owner_password: Password for the owner user (min 8 characters)
    """
    company_name: str = Field(
        ...,
        min_length=2,
        max_length=255,
        description="Company name",
        examples=["Contabilidade Silva & Associados"]
    )
    
    document: Optional[str] = Field(
        None,
        max_length=20,
        description="Company document (CNPJ/CPF)",
        examples=["12.345.678/0001-90"]
    )
    
    owner_email: EmailStr = Field(
        ...,
        description="Owner email address (will be validated)",
        examples=["joao.silva@contabilidade.com"]
    )
    
    owner_password: str = Field(
        ...,
        min_length=8,
        description="Owner password (minimum 8 characters)",
        examples=["SecurePass123!"]
    )

    owner_full_name: Optional[str] = Field(
        None,
        max_length=255,
        description="Owner full name",
        examples=["João Silva"]
    )

    plan_slug: Optional[str] = Field(
        None,
        description="Subscription plan slug",
        examples=["free", "starter", "pro"]
    )


class TenantRegistrationResponse(BaseModel):
    """
    Schema for tenant registration response.
    
    Returned after successful tenant and owner user creation.
    """
    message: str = Field(
        ...,
        description="Success message"
    )
    
    tenant_id: str = Field(
        ...,
        description="Created tenant UUID"
    )
    
    user_id: str = Field(
        ...,
        description="Created owner user UUID"
    )
    
    owner_email: str = Field(
        ...,
        description="Owner email address"
    )
