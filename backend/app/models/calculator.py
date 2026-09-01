"""Calculator models for Feature #7 — Calculadora Fiscal com IA."""

import uuid
import enum
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, JSON, Numeric, String, Text, UUID as SQLUUID, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.models.base import Base, TenantBase


class TaxRegime(str, enum.Enum):
    """Brazilian tax regime options."""
    SIMPLES_NACIONAL = "simples_nacional"
    LUCRO_PRESUMIDO = "lucro_presumido"
    LUCRO_REAL = "lucro_real"
    MEI = "mei"


class SimulationStatus(str, enum.Enum):
    """Status of a calculator simulation."""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class CalculatorSimulation(Base, TenantBase):
    """Records a fiscal regime simulation run by the user."""

    __tablename__ = "calculator_simulations"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("accounting_clients.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Input parameters
    annual_revenue: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    activity_type: Mapped[str] = mapped_column(String(255), nullable=False)
    cnae_code: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    state: Mapped[Optional[str]] = mapped_column(String(2), nullable=True)
    has_employees: Mapped[bool] = mapped_column(nullable=False, default=False)
    employee_count: Mapped[int] = mapped_column(nullable=False, default=0)
    payroll_total: Mapped[Optional[Decimal]] = mapped_column(Numeric(15, 2), nullable=True)

    # Results (JSON for flexibility)
    results: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    recommended_regime: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    ai_recommendation: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    status: Mapped[SimulationStatus] = mapped_column(
        SQLEnum(
            SimulationStatus,
            name="simulation_status_enum",
            create_type=False,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SimulationStatus.PENDING,
        index=True,
    )

    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class FiscalAssistantMessage(Base, TenantBase):
    """Chat messages with the AI fiscal assistant."""

    __tablename__ = "fiscal_assistant_messages"

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Tenant identifier for data isolation",
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    simulation_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        SQLUUID(as_uuid=True),
        ForeignKey("calculator_simulations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    role: Mapped[str] = mapped_column(String(16), nullable=False, comment="user or assistant")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tokens_used: Mapped[int] = mapped_column(nullable=False, default=0)
