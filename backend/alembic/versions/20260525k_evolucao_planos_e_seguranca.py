"""evolucao_planos_e_seguranca

Revision ID: 20260525k
Revises: 20260525j
Create Date: 2026-05-25 00:00:00.000000

Changes:
- Add two_factor_enabled, two_factor_secret, two_factor_method columns to users table
- Insert annual plan seeds aligned with the current plans table schema
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260525k"
down_revision = "20260525j"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "two_factor_enabled",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether two-factor authentication is enabled for this user",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "two_factor_secret",
            sa.String(64),
            nullable=True,
            comment="Encrypted TOTP secret (base32) for Google Authenticator",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "two_factor_method",
            sa.String(10),
            nullable=False,
            server_default=sa.text("'none'"),
            comment="Method: none | totp | email",
        ),
    )

    op.execute(
        """
        INSERT INTO plans (
            id,
            slug,
            name,
            description,
            price_monthly,
            max_clients,
            max_users,
            max_ai_calls_month,
            max_documents_per_client,
            features,
            active
        )
        VALUES
          (
            gen_random_uuid(),
            'intermediario_anual',
            'Intermediario Anual',
            'Plano anual para escritorios em crescimento com economia de dois meses.',
            119.00,
            80,
            5,
            20,
            100,
            '{"calculator": true, "ai_chat": true, "pdf_export": false, "portal_cliente": true, "obrigacoes": true, "annual_plan": true}'::jsonb,
            true
          ),
          (
            gen_random_uuid(),
            'premium_anual',
            'Premium Anual',
            'Plano anual sem limites operacionais com economia de dois meses.',
            239.00,
            NULL,
            NULL,
            NULL,
            NULL,
            '{"calculator": true, "ai_chat": true, "pdf_export": true, "portal_cliente": true, "obrigacoes": true, "annual_plan": true}'::jsonb,
            true
          ),
          (
            gen_random_uuid(),
            'enterprise',
            'Enterprise',
            'Plano corporativo com migracao assistida, SLA dedicado e contrato personalizado.',
            NULL,
            NULL,
            NULL,
            NULL,
            NULL,
            '{"calculator": true, "ai_chat": true, "pdf_export": true, "portal_cliente": true, "obrigacoes": true, "enterprise": true, "migration_assisted": true}'::jsonb,
            true
          )
        ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM plans WHERE slug IN ('intermediario_anual', 'premium_anual', 'enterprise');"
    )

    op.drop_column("users", "two_factor_method")
    op.drop_column("users", "two_factor_secret")
    op.drop_column("users", "two_factor_enabled")
