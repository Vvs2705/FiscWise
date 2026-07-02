"""create billing_charges (Mercado Pago local charge intent)

Local charge created BEFORE talking to the gateway, mirroring SessãoInk's P0-06
pattern: ``external_reference`` and ``idempotency_key`` use the local charge id
(never the tenant_id), so the tenant is not leaked and distinct checkouts do not
collapse. The subscription is only activated after the payment/preapproval is
reconciled against the gateway (webhook).

Revision ID: j3b145a829ef
Revises: i3b145a829ef
Create Date: 2026-07-02 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'j3b145a829ef'
down_revision: Union[str, None] = 'i3b145a829ef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'billing_charges',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Optional link to plans.id (billing prices are '
                          'server-side; plan may not carry the sale price)'),
        sa.Column('plan_slug', sa.String(50), nullable=False,
                  comment='Billing plan slug: escritorio | escritorio_pro'),
        sa.Column('ciclo', sa.String(20), nullable=False,
                  comment='Billing cycle: mensal | anual'),
        sa.Column('metodo', sa.String(20), nullable=True,
                  comment='Intended method hint: pix | card | boleto'),
        sa.Column('amount_cents', sa.Integer(), nullable=False,
                  comment='Server-computed sale amount in cents (BRL)'),
        sa.Column('moeda', sa.String(3), server_default='BRL', nullable=False),
        sa.Column('status', sa.String(30), server_default='CRIADA', nullable=False,
                  comment='CRIADA | ENVIADA_GATEWAY | PENDENTE | PAGA | '
                          'EXPIRADA | CANCELADA | FALHA'),
        sa.Column('gateway', sa.String(40), server_default='mercadopago',
                  nullable=False),
        sa.Column('gateway_preference_id', sa.String(200), nullable=True),
        sa.Column('gateway_preapproval_id', sa.String(200), nullable=True),
        sa.Column('external_reference', sa.String(64), nullable=False),
        sa.Column('idempotency_key', sa.String(64), nullable=False),
        sa.Column('init_point', sa.String(500), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE',
                                name='fk_billing_charge_tenant'),
        sa.UniqueConstraint('external_reference',
                            name='uq_billing_charge_external_reference'),
    )
    op.create_index('idx_billing_charge_tenant', 'billing_charges', ['tenant_id'])
    op.create_index('idx_billing_charge_status', 'billing_charges', ['status'])
    op.create_index('idx_billing_charge_external_reference',
                    'billing_charges', ['external_reference'], unique=True)


def downgrade() -> None:
    op.drop_index('idx_billing_charge_external_reference', table_name='billing_charges')
    op.drop_index('idx_billing_charge_status', table_name='billing_charges')
    op.drop_index('idx_billing_charge_tenant', table_name='billing_charges')
    op.drop_table('billing_charges')
