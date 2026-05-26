"""evolve_clients_for_obligations

Revision ID: g3b145a829ef
Revises: f3b145a829ef
Create Date: 2026-05-26 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'g3b145a829ef'
down_revision: Union[str, None] = 'f3b145a829ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('accounting_clients', sa.Column('cnae', sa.String(length=7), nullable=True))
    op.add_column('accounting_clients', sa.Column('regime_tributario', sa.String(length=20), nullable=True))
    op.add_column('accounting_clients', sa.Column('municipio_ibge', sa.String(length=7), nullable=True))
    op.add_column('accounting_clients', sa.Column('uf', sa.String(length=2), nullable=True))
    op.add_column('accounting_clients', sa.Column('tem_funcionarios', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('accounting_clients', sa.Column('inscricao_estadual', sa.String(length=30), nullable=True))
    op.add_column('accounting_clients', sa.Column('inscricao_municipal', sa.String(length=30), nullable=True))

def downgrade() -> None:
    op.drop_column('accounting_clients', 'inscricao_municipal')
    op.drop_column('accounting_clients', 'inscricao_estadual')
    op.drop_column('accounting_clients', 'tem_funcionarios')
    op.drop_column('accounting_clients', 'uf')
    op.drop_column('accounting_clients', 'municipio_ibge')
    op.drop_column('accounting_clients', 'regime_tributario')
    op.drop_column('accounting_clients', 'cnae')
