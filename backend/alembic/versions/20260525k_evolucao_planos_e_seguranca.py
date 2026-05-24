"""evolucao_planos_e_seguranca

Revision ID: 20260525k
Revises: 20260525j_rls_slice_two_policies
Create Date: 2026-05-25 00:00:00.000000

Changes:
- Add two_factor_enabled, two_factor_secret, two_factor_method columns to users table
- Insert annual plan seeds (intermediario_anual, premium_anual, enterprise)
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260525k"
down_revision = "20260525j_rls_slice_two_policies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── 2FA columns on users ──────────────────────────────────────────────────
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

    # ── New plan seeds ────────────────────────────────────────────────────────
    # Using execute with raw SQL for simplicity
    op.execute(
        """
        INSERT INTO plans (slug, display_name, price_cents, max_clients, max_users,
                           ai_summary_quota, features, is_active)
        VALUES
          ('intermediario_anual', 'Intermediário Anual', 142800, 80, 5, 240,
           '["Até 80 clientes","5 usuários","IA Fiscal (20 msgs/mês)","Motor de obrigações","Portal do cliente","Suporte prioritário","2 meses grátis"]',
           true),
          ('premium_anual', 'Premium Anual', 286800, 2147483647, 2147483647, -1,
           '["Clientes ilimitados","Usuários ilimitados","IA Fiscal ilimitada","Export PDF","Todas as funcionalidades","Suporte dedicado","2 meses grátis"]',
           true),
          ('enterprise', 'Enterprise', 0, 2147483647, 2147483647, -1,
           '["Tudo do Premium","Migração de sistema legado","SLA dedicado","Treinamento","Contrato personalizado","Faturamento customizado"]',
           true)
        ON CONFLICT (slug) DO NOTHING;
        """
    )


def downgrade() -> None:
    # Remove plan seeds
    op.execute(
        "DELETE FROM plans WHERE slug IN ('intermediario_anual', 'premium_anual', 'enterprise');"
    )

    # Remove 2FA columns
    op.drop_column("users", "two_factor_method")
    op.drop_column("users", "two_factor_secret")
    op.drop_column("users", "two_factor_enabled")
