"""users.welcome_tour_seen_at: o tour de boas-vindas aparece só no primeiro acesso.

Contas que já existem ficam marcadas como "já viu", para o tour não aparecer
de novo para quem já usa o sistema.

Revision ID: p2j8cd50hl7
Revises: o1i7bc49gk6
Create Date: 2026-11-12
"""

from alembic import op
import sqlalchemy as sa

revision = "p2j8cd50hl7"
down_revision = "o1i7bc49gk6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("welcome_tour_seen_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.execute("UPDATE users SET welcome_tour_seen_at = now() WHERE welcome_tour_seen_at IS NULL")


def downgrade() -> None:
    op.drop_column("users", "welcome_tour_seen_at")
