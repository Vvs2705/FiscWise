"""Add tenant_subscriptions table

Revision ID: 20260525f
Revises: 20260525e
Create Date: 2026-05-25 16:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260525f'
down_revision = '20260525e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'tenant_subscriptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False,
                  unique=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), nullable=False),

        # Payment provider
        sa.Column('billing_provider', sa.String(20), nullable=True,
                  comment='asaas | iugu | manual'),
        sa.Column('provider_customer_id', sa.String(200), nullable=True,
                  comment='Customer ID on billing provider'),
        sa.Column('provider_subscription_id', sa.String(200), nullable=True,
                  comment='Subscription ID on billing provider'),

        # Status
        sa.Column('status', sa.String(30), nullable=False, server_default='trialing',
                  comment='trialing | active | past_due | suspended | cancelled'),

        # Billing period
        sa.Column('current_period_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('trial_ends_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),

        # Grace period: days allowed after due before suspension
        sa.Column('grace_period_days', sa.Integer, server_default='3', nullable=False),

        # Billing amounts (snapshot at subscription creation)
        sa.Column('amount', sa.Numeric(10, 2), nullable=True),
        sa.Column('currency', sa.String(3), server_default='BRL', nullable=False),

        # Last webhook event for idempotency
        sa.Column('last_event_id', sa.String(200), nullable=True),
        sa.Column('last_event_at', sa.DateTime(timezone=True), nullable=True),

        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),

        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id'], ondelete='CASCADE',
                                name='fk_tenant_subscription_tenant'),
        sa.ForeignKeyConstraint(['plan_id'], ['plans.id'], ondelete='RESTRICT',
                                name='fk_tenant_subscription_plan'),
    )
    op.create_index('idx_tenant_sub_tenant', 'tenant_subscriptions', ['tenant_id'])
    op.create_index('idx_tenant_sub_status', 'tenant_subscriptions', ['status'])
    op.create_index('idx_tenant_sub_provider_ids',
                    'tenant_subscriptions',
                    ['billing_provider', 'provider_subscription_id'])

    # Webhook events log (for idempotency and audit)
    op.create_table(
        'billing_webhook_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('provider', sa.String(20), nullable=False),
        sa.Column('event_id', sa.String(200), nullable=False,
                  comment='Provider-issued event ID for idempotency'),
        sa.Column('event_type', sa.String(100), nullable=False),
        sa.Column('payload', postgresql.JSONB, nullable=False),
        sa.Column('processed', sa.Boolean, server_default='false', nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider', 'event_id',
                            name='uq_billing_webhook_provider_event'),
    )
    op.create_index('idx_billing_webhook_unprocessed',
                    'billing_webhook_events', ['processed', 'created_at'])


def downgrade() -> None:
    op.drop_index('idx_billing_webhook_unprocessed', table_name='billing_webhook_events')
    op.drop_table('billing_webhook_events')
    op.drop_index('idx_tenant_sub_provider_ids', table_name='tenant_subscriptions')
    op.drop_index('idx_tenant_sub_status', table_name='tenant_subscriptions')
    op.drop_index('idx_tenant_sub_tenant', table_name='tenant_subscriptions')
    op.drop_table('tenant_subscriptions')
