"""users.password_expired: troca obrigatória de senha no próximo acesso.

Também expira a senha de toda conta que tinha o MESMO hash bcrypt de outra
conta mais antiga. Com sal aleatório, hash igual só acontece quando alguém
copiou o hash (o antigo backend/create_gisele.py criava um OWNER assim): a
conta mais nova passa a exigir senha nova no próximo login e as sessões
abertas dela caem. A conta original fica como está.

Revision ID: z2c3senhaexpirada
Revises: y1b2totpcifrado
Create Date: 2026-11-21
"""

from alembic import op
import sqlalchemy as sa

revision = "z2c3senhaexpirada"
down_revision = "y1b2totpcifrado"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_expired", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.execute(
        """
        UPDATE users AS u
           SET password_expired = TRUE,
               tokens_valid_after = CURRENT_TIMESTAMP
         WHERE EXISTS (
               SELECT 1 FROM users AS o
                WHERE o.hashed_password = u.hashed_password
                  AND o.id <> u.id
                  AND (o.created_at < u.created_at
                       OR (o.created_at = u.created_at AND o.id < u.id))
         )
        """
    )


def downgrade() -> None:
    op.drop_column("users", "password_expired")
