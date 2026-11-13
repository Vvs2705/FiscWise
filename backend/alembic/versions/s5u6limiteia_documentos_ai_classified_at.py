"""client_documents.ai_classified_at: conta a classificação por IA no saldo do plano.

A classificação automática de documentos passa a usar o mesmo saldo mensal de
IA do plano (plans.max_ai_calls_month). A coluna marca quando o documento foi
classificado. Documentos antigos ficam sem data: a contagem começa agora, sem
gastar o saldo deste mês de quem já usava.

Revision ID: s5u6limiteia
Revises: r4t5teste14d
Create Date: 2026-11-13
"""

from alembic import op
import sqlalchemy as sa

revision = "s5u6limiteia"
down_revision = "r4t5teste14d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "client_documents",
        sa.Column("ai_classified_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "idx_documents_tenant_ai_classified",
        "client_documents",
        ["tenant_id", "ai_classified_at"],
    )


def downgrade() -> None:
    op.drop_index("idx_documents_tenant_ai_classified", table_name="client_documents")
    op.drop_column("client_documents", "ai_classified_at")
