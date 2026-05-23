"""
Calculator Schemas for FiscWise - Feature #7

Pydantic v2 DTOs for all calculator endpoints:
- Regime comparison simulation
- ICMS simulation
- PIS/COFINS simulation
- AI chat messages
- Simulation history
- PDF export (PREMIUM only)
"""

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Shared enums (mirrored from models for schema independence)
# ---------------------------------------------------------------------------

from app.models.calculator import AssistantRole, SimulationType, TaxRegime


# ---------------------------------------------------------------------------
# Regime simulation
# ---------------------------------------------------------------------------

class RegimeSimulationCreate(BaseModel):
    """Input for comparing the three Brazilian tax regimes."""

    model_config = ConfigDict(str_strip_whitespace=True)

    # Core financials (annual figures in BRL)
    annual_revenue: Decimal = Field(
        ...,
        gt=0,
        description="Annual gross revenue (Receita Bruta Anual) in BRL",
        examples=[1_200_000.00],
    )
    annual_costs: Decimal = Field(
        ...,
        ge=0,
        description="Total annual deductible costs in BRL",
        examples=[800_000.00],
    )
    annual_payroll: Decimal = Field(
        default=Decimal("0"),
        ge=0,
        description="Total annual payroll (Folha de Salarios) in BRL",
        examples=[200_000.00],
    )

    # CNAE / activity
    activity_code: Optional[str] = Field(
        default=None,
        max_length=20,
        description="CNAE activity code (for Simples Nacional annex selection)",
        examples=["6201500"],
    )

    # Optional DRE data for richer AI analysis
    cogs: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="Cost of Goods Sold (CMV) in BRL",
    )
    gross_profit: Optional[Decimal] = Field(
        default=None,
        description="Gross profit in BRL (revenue - COGS)",
    )

    title: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Optional title for this simulation",
    )

    @field_validator("annual_revenue", "annual_costs", "annual_payroll", mode="before")
    @classmethod
    def coerce_decimal(cls, v: Any) -> Decimal:
        if isinstance(v, float):
            return Decimal(str(v))
        return Decimal(v) if not isinstance(v, Decimal) else v


class TaxScenarioResponse(BaseModel):
    """Single regime scenario in a comparison result."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    regime: TaxRegime
    annual_revenue: Decimal
    effective_rate: Decimal
    total_tax: Decimal
    tax_breakdown: dict[str, Any]
    is_recommended: bool


class RegimeSimulationResponse(BaseModel):
    """Full result of a regime comparison simulation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_type: SimulationType
    title: Optional[str]
    input_data: dict[str, Any]
    result_data: dict[str, Any]
    ai_recommendation: Optional[str]
    scenarios: list[TaxScenarioResponse]
    created_at: datetime


# ---------------------------------------------------------------------------
# ICMS simulation
# ---------------------------------------------------------------------------

class IcmsSimulationCreate(BaseModel):
    """Input for ICMS calculation by NCM and state."""

    model_config = ConfigDict(str_strip_whitespace=True)

    ncm_code: str = Field(
        ...,
        min_length=8,
        max_length=10,
        pattern=r"^\d{4}\.?\d{2}\.?\d{2}$",
        description="NCM code (8 digits, with or without dots)",
        examples=["8471.30.12"],
    )

    origin_state: str = Field(
        ...,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="Origin state UF (e.g. SP, RJ, MG)",
        examples=["SP"],
    )

    destination_state: str = Field(
        ...,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="Destination state UF",
        examples=["RJ"],
    )

    operation_value: Decimal = Field(
        ...,
        gt=0,
        description="Operation value in BRL",
        examples=[50_000.00],
    )

    # Indicates if buyer is ICMS taxpayer (contribuinte)
    is_buyer_taxpayer: bool = Field(
        default=True,
        description="Whether the buyer is an ICMS taxpayer (contribuinte)",
    )

    title: Optional[str] = Field(
        default=None,
        max_length=255,
    )

    @field_validator("origin_state", "destination_state", mode="before")
    @classmethod
    def uppercase_state(cls, v: str) -> str:
        return v.strip().upper()

    @field_validator("ncm_code", mode="before")
    @classmethod
    def clean_ncm(cls, v: str) -> str:
        # Normalise to format XXXX.XX.XX
        digits = "".join(c for c in str(v) if c.isdigit())
        if len(digits) == 8:
            return f"{digits[:4]}.{digits[4:6]}.{digits[6:8]}"
        return v.strip()


class IcmsSimulationResponse(BaseModel):
    """Result of an ICMS simulation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_type: SimulationType
    title: Optional[str]
    input_data: dict[str, Any]
    result_data: dict[str, Any]
    ai_recommendation: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# PIS/COFINS simulation
# ---------------------------------------------------------------------------

class PisCofinsSimulationCreate(BaseModel):
    """Input for PIS/COFINS calculation."""

    model_config = ConfigDict(str_strip_whitespace=True)

    monthly_revenue: Decimal = Field(
        ...,
        gt=0,
        description="Monthly gross revenue in BRL",
        examples=[100_000.00],
    )

    # Cumulative (Lucro Presumido / Simples) or Non-Cumulative (Lucro Real)
    is_non_cumulative: bool = Field(
        default=False,
        description="True = Lucro Real (non-cumulative), False = Lucro Presumido (cumulative)",
    )

    # Deductible credits (only meaningful for non-cumulative)
    deductible_credits: Optional[Decimal] = Field(
        default=None,
        ge=0,
        description="PIS/COFINS credits to deduct (non-cumulative only)",
    )

    activity_description: Optional[str] = Field(
        default=None,
        max_length=255,
        description="Description of the main activity (for AI context)",
    )

    title: Optional[str] = Field(default=None, max_length=255)

    @field_validator("monthly_revenue", "deductible_credits", mode="before")
    @classmethod
    def coerce_decimal(cls, v: Any) -> Optional[Decimal]:
        if v is None:
            return None
        if isinstance(v, float):
            return Decimal(str(v))
        return Decimal(v) if not isinstance(v, Decimal) else v


class PisCofinsSimulationResponse(BaseModel):
    """Result of a PIS/COFINS simulation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_type: SimulationType
    title: Optional[str]
    input_data: dict[str, Any]
    result_data: dict[str, Any]
    ai_recommendation: Optional[str]
    created_at: datetime


# ---------------------------------------------------------------------------
# AI Chat
# ---------------------------------------------------------------------------

class AssistantMessageCreate(BaseModel):
    """User message to the fiscal AI assistant."""

    model_config = ConfigDict(str_strip_whitespace=True)

    content: str = Field(
        ...,
        min_length=1,
        max_length=4_000,
        description="User message content",
    )

    simulation_id: Optional[uuid.UUID] = Field(
        default=None,
        description="Optional simulation ID to anchor the conversation",
    )


class AssistantMessageResponse(BaseModel):
    """A single message in the chat conversation."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    role: AssistantRole
    content: str
    simulation_id: Optional[uuid.UUID]
    tokens_used: Optional[int]
    created_at: datetime


class ChatResponse(BaseModel):
    """Response from the AI chat endpoint (user + assistant messages)."""

    user_message: AssistantMessageResponse
    assistant_message: AssistantMessageResponse
    # Remaining chat quota for the current month (None = unlimited)
    remaining_quota: Optional[int]


# ---------------------------------------------------------------------------
# Simulation history
# ---------------------------------------------------------------------------

class SimulationListItem(BaseModel):
    """Lightweight simulation entry for the history list."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    simulation_type: SimulationType
    title: Optional[str]
    plan_slug: Optional[str]
    created_at: datetime


class SimulationHistoryResponse(BaseModel):
    """Paginated simulation history."""

    items: list[SimulationListItem]
    total: int
    page: int
    page_size: int


# ---------------------------------------------------------------------------
# PDF export (PREMIUM only)
# ---------------------------------------------------------------------------

class PdfExportRequest(BaseModel):
    """Request body for PDF report generation."""

    simulation_id: uuid.UUID = Field(
        ...,
        description="ID of the simulation to export",
    )

    include_ai_recommendation: bool = Field(
        default=True,
        description="Include AI recommendation section in the report",
    )
