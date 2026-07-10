"""Precos definidos por analise de mercado (premium 349) + ciclo de cobranca na assinatura.

- premium: R$299 -> R$349 (analise de mercado 09/07/2026: 12% abaixo do Calima Pro
  com limites maiores; intermediario mantem R$149).
- tenant_subscriptions.billing_cycle: mensal | trimestral | semestral | anual
  (necessario para o webhook validar o valor pago do ciclo antes de ativar).

Revision ID: j4d267c94bf1
Revises: i3b145a829ef
Create Date: 2026-07-10
"""
from alembic import op
import sqlalchemy as sa

revision = 'j4d267c94bf1'
down_revision = 'i3b145a829ef'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("UPDATE plans SET price_monthly = 349.00 WHERE slug = 'premium'")
    op.add_column(
        'tenant_subscriptions',
        sa.Column('billing_cycle', sa.String(length=20),
                  server_default='mensal', nullable=False),
    )


def downgrade() -> None:
    op.drop_column('tenant_subscriptions', 'billing_cycle')
    op.execute("UPDATE plans SET price_monthly = 299.00 WHERE slug = 'premium'")
