"""Textos dos planos com acentuação correta (vitrine e aba Plano).

Revision ID: p2j8cd50hl7
Revises: o1i7bc49gk6
Create Date: 2026-11-12
"""
from alembic import op

revision = 'p2j8cd50hl7'
down_revision = 'o1i7bc49gk6'
branch_labels = None
depends_on = None

_NOVOS = {
    'free': ('Gratuito', 'Para experimentar o FiscWise com uma carteira pequena.'),
    'intermediario': ('Intermediário', 'Para escritórios em crescimento: portal do cliente, calendário de obrigações e IA fiscal.'),
    'premium': ('Premium', 'Sem limite de clientes e usuários, com dossiê em PDF e IA fiscal sem limite mensal.'),
    'enterprise': ('Enterprise', 'Para redes e grandes escritórios: migração assistida, SLA dedicado e contrato personalizado.'),
    'intermediario_anual': ('Intermediário Anual', 'Plano anual para escritórios em crescimento, com economia de dois meses.'),
    'premium_anual': ('Premium Anual', 'Plano anual sem limites operacionais, com economia de dois meses.'),
}


def upgrade() -> None:
    for slug, (name, desc) in _NOVOS.items():
        op.execute(
            f"UPDATE plans SET name = '{name}', description = '{desc}' WHERE slug = '{slug}'"
        )


def downgrade() -> None:
    # Só texto: manter os novos é seguro.
    pass
