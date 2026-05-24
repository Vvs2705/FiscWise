"""Add annual_adjustment_percent to accounting_clients

Revision ID: 20260525e
Revises: 20260525d
Create Date: 2026-05-25 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa

revision = '20260525e'
down_revision = '20260525d'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add annual fee adjustment percentage (e.g., 5.0 = 5% annual IPCA reajuste)
    op.add_column(
        'accounting_clients',
        sa.Column(
            'annual_adjustment_percent',
            sa.Numeric(5, 2),
            nullable=True,
            comment='Annual fee adjustment percentage (e.g. 5.00 = 5% IPCA). Applied on billing anniversary.',
        ),
    )


def downgrade() -> None:
    op.drop_column('accounting_clients', 'annual_adjustment_percent')
