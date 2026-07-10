"""Desativa pseudo-planos anuais legados (viraram brecha de desconto duplo).

Com os ciclos por plano (j4d267c94bf1: Pix -15%, anual -15%), os planos
'intermediario_anual' (R$119) e 'premium_anual' (R$239) — que embutiam o
desconto anual no preco mensal — permitiriam assinar MENSAL recorrente pelo
preco ja descontado e ainda ganhar -15% de Pix em cima. Desativa (reversivel);
o ciclo anual agora e escolhido no checkout do plano normal.

Revision ID: k5e378d05cg2
Revises: j4d267c94bf1
Create Date: 2026-07-10
"""
from alembic import op

revision = 'k5e378d05cg2'
down_revision = 'j4d267c94bf1'
branch_labels = None
depends_on = None

_LEGADOS = "('intermediario_anual', 'premium_anual')"


def upgrade() -> None:
    op.execute(f"UPDATE plans SET active = false WHERE slug IN {_LEGADOS}")


def downgrade() -> None:
    op.execute(f"UPDATE plans SET active = true WHERE slug IN {_LEGADOS}")
