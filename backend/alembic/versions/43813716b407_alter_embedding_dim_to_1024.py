"""alter_embedding_dim_to_1024

Revision ID: 43813716b407
Revises: 394d97d5da14
Create Date: 2026-04-27 15:21:02.947076

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = '43813716b407'
down_revision: Union[str, None] = '394d97d5da14'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1024)")


def downgrade() -> None:
    op.execute("ALTER TABLE document_chunks ALTER COLUMN embedding TYPE vector(1536)")
