"""evolve_certificates

Revision ID: 0f0c2c42addb
Revises: 6b7b8687843d
Create Date: 2026-05-26 08:54:33.874064

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '0f0c2c42addb'
down_revision: Union[str, None] = '6b7b8687843d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('digital_certificates', sa.Column('uso_autorizado', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=True))
    op.add_column('digital_certificates', sa.Column('ultimo_uso', sa.DateTime(timezone=True), nullable=True))
    op.add_column('digital_certificates', sa.Column('bloqueado', sa.Boolean(), server_default='false', nullable=True))
    op.add_column('digital_certificates', sa.Column('motivo_bloqueio', sa.String(length=255), nullable=True))

def downgrade() -> None:
    op.drop_column('digital_certificates', 'motivo_bloqueio')
    op.drop_column('digital_certificates', 'bloqueado')
    op.drop_column('digital_certificates', 'ultimo_uso')
    op.drop_column('digital_certificates', 'uso_autorizado')
