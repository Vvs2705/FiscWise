"""Exclusão automática dos dados de contas vencidas: marcas no escritório.

Pedido do dono (14/11/2026): 60 dias depois de a conta vencer (teste sem
assinatura, assinatura cancelada/suspensa ou pré-pago vencido), os dados são
excluídos automaticamente, com e-mail ao responsável pelo menos 72 horas antes
(app/services/exclusao_dados.py).

- tenants.exclusao_avisada_em: quando o aviso foi aceito pelo provedor de e-mail.
  Sem aviso registrado, nada é excluído.
- tenants.dados_excluidos_em: quando os dados foram excluídos.

Revision ID: w9y0exclusao
Revises: v8x9ajustes
Create Date: 2026-11-14
"""

from alembic import op
import sqlalchemy as sa

revision = "w9y0exclusao"
down_revision = "v8x9ajustes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("tenants", sa.Column("exclusao_avisada_em", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tenants", sa.Column("dados_excluidos_em", sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column("tenants", "dados_excluidos_em")
    op.drop_column("tenants", "exclusao_avisada_em")
