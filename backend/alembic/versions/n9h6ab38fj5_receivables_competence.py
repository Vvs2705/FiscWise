"""receivables.competence + índice único: honorário mensal sem duplicar (DB-5).

A idempotência da cobrança mensal era um LIKE na descrição; com duas execuções
simultâneas (ou uma descrição editada) o honorário saía em dobro.

Revision ID: n9h6ab38fj5
Revises: m8g59af27ei4
Create Date: 2026-10-25
"""

from alembic import op
import sqlalchemy as sa

revision = "n9h6ab38fj5"
down_revision = "m8g59af27ei4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("account_receivables", sa.Column("competence", sa.String(7), nullable=True))
    op.create_index(
        "uq_receivables_tenant_client_competence",
        "account_receivables",
        ["tenant_id", "client_id", "competence"],
        unique=True,
        postgresql_where=sa.text("competence IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_receivables_tenant_client_competence", table_name="account_receivables")
    op.drop_column("account_receivables", "competence")
