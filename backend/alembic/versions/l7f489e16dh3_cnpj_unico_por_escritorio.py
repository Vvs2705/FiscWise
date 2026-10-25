"""CNPJ/CPF único por escritório em accounting_clients (DB-4).

A checagem existia só no POST /clients; edição, importação e requisições
simultâneas cadastravam o mesmo documento duas vezes no mesmo escritório.
Índice parcial: clientes sem documento continuam permitidos.

Se a base já tiver duplicados, o upgrade falha de propósito: deduplique antes
(SELECT tenant_id, document, count(*) FROM accounting_clients
 WHERE document IS NOT NULL GROUP BY 1, 2 HAVING count(*) > 1).

Revision ID: l7f489e16dh3
Revises: k5e378d05cg2
Create Date: 2026-10-25
"""

from alembic import op
import sqlalchemy as sa

revision = "l7f489e16dh3"
down_revision = "k5e378d05cg2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "uq_clients_tenant_document",
        "accounting_clients",
        ["tenant_id", "document"],
        unique=True,
        postgresql_where=sa.text("document IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("uq_clients_tenant_document", table_name="accounting_clients")
