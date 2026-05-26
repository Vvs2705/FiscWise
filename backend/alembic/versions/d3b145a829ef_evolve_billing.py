"""evolve_billing

Revision ID: d3b145a829ef
Revises: 0f0c2c42addb
Create Date: 2026-05-26 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'd3b145a829ef'
down_revision: Union[str, None] = '0f0c2c42addb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.add_column('account_receivables', sa.Column('invoice_id', sa.UUID(as_uuid=True), nullable=True))
    op.add_column('account_receivables', sa.Column('nfse_emitida', sa.Boolean(), server_default='false', nullable=True))

def downgrade() -> None:
    op.drop_column('account_receivables', 'nfse_emitida')
    op.drop_column('account_receivables', 'invoice_id')
