"""Feature #7: Calculadora Fiscal com IA

Revision ID: 20260523_fiscal_calculator
Revises: 20260522
Create Date: 2026-05-23 00:00:00.000000

Creates the following tables:
  - calculator_simulations
  - tax_scenarios
  - fiscal_assistant_messages
  - fiscal_benefits

Creates the following enum types:
  - simulation_type_enum
  - tax_regime_enum
  - assistant_role_enum
"""

from typing import Sequence, Union
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from alembic import op

revision: str = "20260523_fiscal_calculator"
down_revision: Union[str, None] = "20260522"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────────
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE simulation_type_enum AS ENUM ('regime', 'icms', 'pis_cofins');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE tax_regime_enum AS ENUM ('simples_nacional', 'lucro_presumido', 'lucro_real');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            CREATE TYPE assistant_role_enum AS ENUM ('user', 'assistant', 'system');
        EXCEPTION WHEN duplicate_object THEN null;
        END $$;
    """)

    # ── calculator_simulations ────────────────────────────────────────────────
    op.create_table(
        "calculator_simulations",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            comment="Primary key UUID",
        ),
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
            comment="Tenant identifier for data isolation",
        ),
        sa.Column(
            "simulation_type",
            postgresql.ENUM(
                "regime", "icms", "pis_cofins",
                name="simulation_type_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(255), nullable=True),
        sa.Column("input_data", sa.JSON(), nullable=False),
        sa.Column("result_data", sa.JSON(), nullable=False),
        sa.Column("ai_recommendation", sa.Text(), nullable=True),
        sa.Column("plan_slug", sa.String(50), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_calculator_simulations_tenant_id",
        "calculator_simulations",
        ["tenant_id"],
    )
    op.create_index(
        "ix_calculator_simulations_simulation_type",
        "calculator_simulations",
        ["simulation_type"],
    )

    # ── tax_scenarios ─────────────────────────────────────────────────────────
    op.create_table(
        "tax_scenarios",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
            comment="Primary key UUID",
        ),
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "simulation_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("calculator_simulations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "regime",
            postgresql.ENUM(
                "simples_nacional", "lucro_presumido", "lucro_real",
                name="tax_regime_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("annual_revenue", sa.Numeric(18, 2), nullable=False),
        sa.Column("effective_rate", sa.Numeric(8, 4), nullable=False),
        sa.Column("total_tax", sa.Numeric(18, 2), nullable=False),
        sa.Column("tax_breakdown", sa.JSON(), nullable=False),
        sa.Column("is_recommended", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_tax_scenarios_tenant_id", "tax_scenarios", ["tenant_id"])
    op.create_index("ix_tax_scenarios_simulation_id", "tax_scenarios", ["simulation_id"])

    # ── fiscal_assistant_messages ─────────────────────────────────────────────
    op.create_table(
        "fiscal_assistant_messages",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "tenant_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("tenants.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "simulation_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("calculator_simulations.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "role",
            postgresql.ENUM(
                "user", "assistant", "system",
                name="assistant_role_enum",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_fiscal_assistant_messages_tenant_id",
        "fiscal_assistant_messages",
        ["tenant_id"],
    )
    op.create_index(
        "ix_fiscal_assistant_messages_simulation_id",
        "fiscal_assistant_messages",
        ["simulation_id"],
    )

    # ── fiscal_benefits ───────────────────────────────────────────────────────
    op.create_table(
        "fiscal_benefits",
        sa.Column(
            "id",
            sa.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("tax_type", sa.String(80), nullable=False, index=True),
        sa.Column("applicable_states", sa.String(255), nullable=True),
        sa.Column("applicable_ncm", sa.String(500), nullable=True),
        sa.Column("applicable_regimes", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_fiscal_benefits_tax_type", "fiscal_benefits", ["tax_type"])
    op.create_index("ix_fiscal_benefits_is_active", "fiscal_benefits", ["is_active"])


def downgrade() -> None:
    op.drop_table("fiscal_benefits")
    op.drop_table("fiscal_assistant_messages")
    op.drop_table("tax_scenarios")
    op.drop_table("calculator_simulations")

    op.execute("DROP TYPE IF EXISTS assistant_role_enum")
    op.execute("DROP TYPE IF EXISTS tax_regime_enum")
    op.execute("DROP TYPE IF EXISTS simulation_type_enum")
