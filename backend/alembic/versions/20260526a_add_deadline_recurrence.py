"""add_deadline_recurrence

Revision ID: 20260526a
Revises: 20260525p
Create Date: 2026-05-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260526a'
down_revision: Union[str, None] = '20260525p'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add columns to deadline_items
    with op.batch_alter_table('deadline_items') as batch_op:
        batch_op.add_column(sa.Column('is_recurring', sa.Boolean(), server_default=sa.text('false'), nullable=False))
        batch_op.add_column(sa.Column('recurrence_interval', sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column('recurrence_parent_id', sa.UUID(), nullable=True))
        batch_op.create_foreign_key(
            'fk_deadline_items_recurrence_parent',
            'deadline_items',
            ['recurrence_parent_id'], ['id'],
            ondelete='SET NULL'
        )


def downgrade() -> None:
    # Drop foreign key and columns
    with op.batch_alter_table('deadline_items') as batch_op:
        batch_op.drop_constraint('fk_deadline_items_recurrence_parent', type_='foreignkey')
        batch_op.drop_column('recurrence_parent_id')
        batch_op.drop_column('recurrence_interval')
        batch_op.drop_column('is_recurring')
