"""Pydantic schemas for the Fiscal Calculator (Feature #7)."""

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------------
# Simulation schemas
# ---------------------------------------------------------------------------

class SimulateRegimeRequest(BaseModel):
    """Input for a fiscal regime simulation."""

    annual_revenue: Decimal = Field(..., gt=0, description="Faturamento anual bruto em R$")
    activity_type: str = Field(..., min_length=3, max_length=255, description="Descrição da atividade principal")
    cnae_code: Optional[str] = Field(default=None, max_length=20)
    state: Optional[str] = Field(default=None, min_length=2, max_length=2, description="UF (ex: SP, RJ)")
    has_employees: bool = Field(default=False)
    employee_count: int = Field(default=0, ge=0)
    payroll_total: Optional[Decimal] = Field(default=None, ge=0, description="Folha de pagamento mensal total em R$")
    client_id: Optional[UUID] = None

    @field_validator("state")
    @classmethod
    def normalize_state(cls, v: Optional[str]) -> Optional[str]:
        return v.upper() if v else v

    @field_validator("annual_revenue")
    @classmethod
    def validate_revenue(cls, v: Decimal) -> Decimal:
        if v <= 0:
            raise ValueError("Faturamento anual deve ser maior que zero")
        return v


class TaxRegimeResult(BaseModel):
    """Tax burden result for a single regime."""

    regime: str
    regime_label: str
    annual_tax_burden: Decimal
    effective_rate: Decimal
    monthly_installment: Decimal
    eligible: bool
    ineligibility_reason: Optional[str] = None
    breakdown: dict[str, Any] = Field(default_factory=dict)


class SimulateRegimeResponse(BaseModel):
    """Response for a fiscal regime simulation."""

    simulation_id: UUID
    annual_revenue: Decimal
    results: list[TaxRegimeResult]
    recommended_regime: Optional[str] = None
    ai_recommendation: Optional[str] = None
    plan_required_for_ai: Optional[str] = None

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# ICMS simulation
# ---------------------------------------------------------------------------

class SimulateIcmsRequest(BaseModel):
    """Input for ICMS simulation."""

    origin_state: str = Field(..., min_length=2, max_length=2)
    destination_state: str = Field(..., min_length=2, max_length=2)
    transaction_value: Decimal = Field(..., gt=0)
    product_ncm: Optional[str] = Field(default=None, max_length=10)

    @field_validator("origin_state", "destination_state")
    @classmethod
    def upper_state(cls, v: str) -> str:
        return v.upper()


class SimulateIcmsResponse(BaseModel):
    """Response for ICMS simulation."""

    origin_state: str
    destination_state: str
    transaction_value: Decimal
    icms_origin_rate: Decimal
    icms_destination_rate: Decimal
    difal_applicable: bool
    icms_due_origin: Decimal
    icms_due_destination: Decimal
    total_icms: Decimal
    effective_rate: Decimal


# ---------------------------------------------------------------------------
# PIS/COFINS simulation
# ---------------------------------------------------------------------------

class SimulatePisCofinsRequest(BaseModel):
    """Input for PIS/COFINS simulation."""

    regime: str = Field(..., description="lucro_real or lucro_presumido")
    monthly_revenue: Decimal = Field(..., gt=0)
    deductible_costs: Optional[Decimal] = Field(default=None, ge=0)

    @field_validator("regime")
    @classmethod
    def validate_regime(cls, v: str) -> str:
        allowed = {"lucro_real", "lucro_presumido"}
        if v not in allowed:
            raise ValueError(f"Regime deve ser um de: {', '.join(allowed)}")
        return v


class SimulatePisCofinsResponse(BaseModel):
    """Response for PIS/COFINS simulation."""

    regime: str
    monthly_revenue: Decimal
    pis_rate: Decimal
    cofins_rate: Decimal
    pis_due: Decimal
    cofins_due: Decimal
    total_due: Decimal
    effective_rate: Decimal
    credits_applied: Optional[Decimal] = None


# ---------------------------------------------------------------------------
# AI Chat schemas
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """A single chat message."""

    role: str = Field(..., pattern="^(user|assistant)$")
    content: str = Field(..., min_length=1)


class ChatRequest(BaseModel):
    """Request to send a message to the AI fiscal assistant."""

    message: str = Field(..., min_length=1, max_length=4000)
    simulation_id: Optional[UUID] = None
    history: list[ChatMessage] = Field(default_factory=list)


class ChatResponse(BaseModel):
    """Response from the AI fiscal assistant."""

    message: str
    simulation_id: Optional[UUID] = None
    tokens_used: int = 0


# ---------------------------------------------------------------------------
# Simulation history schemas
# ---------------------------------------------------------------------------

class SimulationHistoryItem(BaseModel):
    """Brief record of a past simulation."""

    id: UUID
    annual_revenue: Decimal
    activity_type: str
    recommended_regime: Optional[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class SimulationDetailResponse(BaseModel):
    """Full detail of a saved simulation."""

    id: UUID
    annual_revenue: Decimal
    activity_type: str
    cnae_code: Optional[str]
    state: Optional[str]
    has_employees: bool
    employee_count: int
    payroll_total: Optional[Decimal]
    results: Optional[list[Any]]
    recommended_regime: Optional[str]
    ai_recommendation: Optional[str]
    status: str
    created_at: datetime
    completed_at: Optional[datetime]

    class Config:
        from_attributes = True
