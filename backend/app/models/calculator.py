"""
Calculator Models for FiscWise - Feature #7

Defines models for the fiscal calculator feature:
- CalculatorSimulation: stores simulation results (regime, ICMS, PIS/COFINS)
- TaxScenario: individual scenario within a simulation
- FiscalAssistantMessage: chat messages with the AI fiscal assistant
- FiscalBenefit: fiscal benefits and incentives catalog
"""

import uuid
import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import (
    String, Text, Numeric, DateTime, Integer, Boolean,
    ForeignKey, Enum as SQLEnum, UUID as SQLUUID, JSON
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class SimulationType(str, enum.Enum):
    """Type of fiscal simulation performed."""
    REGIME = "regime"
    ICMS = "icms"
    PIS_COFINS = "pis_cofins"
    FATOR_R = "fator_r"


class TaxRegime(str, enum.Enum):
    """Brazilian tax regime options."""
    SIMPLES_NACIONAL = "simples_nacional"
    LUCRO_PRESUMIDO = "lucro_presumido"
    LUCRO_REAL = "lucro_real"


class AssistantRole(str, enum.Enum):
    """Role in a chat message."""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class CalculatorSimulation(Base, TenantBase):
    """
    Stores the result of a fiscal calculation simulation.

    Each simulation is scoped to a tenant (multi-tenancy).
    The simulation_data JSON column holds all inputs and outputs
    so they can be reconstructed or re-analysed without extra tables.
    """

    __tablename__ = "calculator_simulations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )

    simulation_type: Mapped[SimulationType] = mapped_column(
        SQLEnum(
            SimulationType,
            name="simulation_type_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        index=True,
        comment="Type of simulation: regime, icms or pis_cofins",
    )

    # Human-readable title auto-generated or provided by the user
    title: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable simulation title",
    )

    # Raw inputs as JSON so any calculator can serialise its own payload
    input_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Simulation input parameters (JSON)",
    )

    # Calculated results as JSON
    result_data: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        comment="Simulation result data (JSON)",
    )

    # Optional AI-generated recommendation text (INTERMEDIARIO/PREMIUM only)
    ai_recommendation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="AI-generated recommendation for this simulation",
    )

    # Which plan tier was active when this simulation was created
    # Stored for audit purposes; does not gate access at query time
    plan_slug: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Subscription plan slug at time of simulation",
    )

    def __repr__(self) -> str:
        return (
            f"<CalculatorSimulation(id={self.id}, "
            f"type={self.simulation_type.value}, "
            f"tenant_id={self.tenant_id})>"
        )


class TaxScenario(Base, TenantBase):
    """
    Individual tax scenario within a regime comparison simulation.

    When comparing Simples Nacional vs Lucro Presumido vs Lucro Real
    the calculation produces one TaxScenario row per regime so that the
    frontend can display them side-by-side.
    """

    __tablename__ = "tax_scenarios"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )

    simulation_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("calculator_simulations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Parent simulation",
    )

    regime: Mapped[TaxRegime] = mapped_column(
        SQLEnum(
            TaxRegime,
            name="tax_regime_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="Tax regime for this scenario",
    )

    # Annual gross revenue used as base
    annual_revenue: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Annual gross revenue (base for calculation)",
    )

    # Effective tax rate calculated for this scenario
    effective_rate: Mapped[Decimal] = mapped_column(
        Numeric(8, 4),
        nullable=False,
        comment="Effective tax rate as a decimal (0.1230 = 12.30%)",
    )

    # Total annual tax amount
    total_tax: Mapped[Decimal] = mapped_column(
        Numeric(18, 2),
        nullable=False,
        comment="Total annual tax amount in BRL",
    )

    # Breakdown stored as JSON for flexibility
    tax_breakdown: Mapped[dict] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
        comment="Detailed breakdown per tax component (JSON)",
    )

    # Whether AI recommends this scenario
    is_recommended: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether AI recommends this as the optimal regime",
    )

    def __repr__(self) -> str:
        return (
            f"<TaxScenario(id={self.id}, "
            f"regime={self.regime.value}, "
            f"effective_rate={self.effective_rate})>"
        )


class FiscalAssistantMessage(Base, TenantBase):
    """
    Chat message exchanged with the AI fiscal assistant.

    INTERMEDIARIO plan: capped at 20 messages per calendar month.
    PREMIUM plan: unlimited.
    FREE plan: access denied.
    """

    __tablename__ = "fiscal_assistant_messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )

    # Optionally linked to a simulation for context
    simulation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("calculator_simulations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Related simulation for contextual chat (optional)",
    )

    role: Mapped[AssistantRole] = mapped_column(
        SQLEnum(
            AssistantRole,
            name="assistant_role_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        comment="Message role: user or assistant",
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Message content",
    )

    # Tokens consumed by this message (for cost tracking)
    tokens_used: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="OpenAI tokens consumed for this message",
    )

    def __repr__(self) -> str:
        return (
            f"<FiscalAssistantMessage(id={self.id}, "
            f"role={self.role.value}, "
            f"tenant_id={self.tenant_id})>"
        )


class FiscalBenefit(Base):
    """
    Catalog of fiscal benefits and tax incentives available in Brazil.

    This is a tenant-independent catalog managed by administrators.
    PREMIUM tenants can query this table to discover applicable benefits.
    """

    __tablename__ = "fiscal_benefits"

    id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
        comment="Benefit unique identifier",
    )

    name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Benefit name",
    )

    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Full description of the fiscal benefit",
    )

    # Which tax applies (ICMS, IPI, PIS, COFINS, IRPJ, CSLL, etc.)
    tax_type: Mapped[str] = mapped_column(
        String(80),
        nullable=False,
        index=True,
        comment="Type of tax this benefit applies to",
    )

    # Which states benefit applies to (comma-separated UF codes or 'federal')
    applicable_states: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Applicable state codes (comma-separated UF or 'federal')",
    )

    # NCM codes this benefit covers (comma-separated or null = all)
    applicable_ncm: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        comment="Applicable NCM codes (comma-separated) or null for all",
    )

    # Which regimes qualify for this benefit
    applicable_regimes: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Tax regimes that qualify (comma-separated regime names)",
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        index=True,
        comment="Whether this benefit is currently available",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<FiscalBenefit(id={self.id}, name='{self.name}', tax={self.tax_type})>"
