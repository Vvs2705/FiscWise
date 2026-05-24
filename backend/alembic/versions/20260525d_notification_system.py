"""Add notification_templates and notification_messages tables

Revision ID: 20260525d
Revises: 20260525c
Create Date: 2026-05-25 14:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = '20260525d'
down_revision = '20260525c'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── notification_templates ─────────────────────────────────────────────────
    op.create_table(
        'notification_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='NULL = global system template'),
        sa.Column('channel', sa.String(20), nullable=False,
                  comment='email | whatsapp | sms'),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('body', sa.Text, nullable=False,
                  comment='Template body with {{variable}} placeholders'),
        sa.Column('variables', postgresql.JSONB, nullable=True,
                  comment='Declared variables and their descriptions'),
        sa.Column('is_active', sa.Boolean, server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenants.id'], ondelete='CASCADE', name='fk_notif_tmpl_tenant'
        ),
    )
    op.create_index('idx_notif_tmpl_tenant_channel',
                    'notification_templates', ['tenant_id', 'channel'])

    # ── notification_messages ──────────────────────────────────────────────────
    op.create_table(
        'notification_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False,
                  server_default=sa.text('gen_random_uuid()')),
        sa.Column('tenant_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('client_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('channel', sa.String(20), nullable=False,
                  comment='email | whatsapp | sms'),
        sa.Column('recipient', sa.String(500), nullable=False,
                  comment='Email address or phone number'),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('subject', sa.String(500), nullable=True),
        sa.Column('body', sa.Text, nullable=False),
        sa.Column('status', sa.String(20), server_default='pending', nullable=False,
                  comment='pending | sent | delivered | failed | skipped'),
        sa.Column('provider', sa.String(50), nullable=True,
                  comment='sendgrid | resend | smtp'),
        sa.Column('provider_message_id', sa.String(200), nullable=True),
        sa.Column('error_message', sa.Text, nullable=True),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(
            ['tenant_id'], ['tenants.id'], ondelete='CASCADE', name='fk_notif_msg_tenant'
        ),
        sa.ForeignKeyConstraint(
            ['client_id'], ['accounting_clients.id'], ondelete='SET NULL', name='fk_notif_msg_client'
        ),
        sa.ForeignKeyConstraint(
            ['template_id'], ['notification_templates.id'], ondelete='SET NULL', name='fk_notif_msg_template'
        ),
    )
    op.create_index('idx_notif_msg_tenant_status',
                    'notification_messages', ['tenant_id', 'status'])
    op.create_index('idx_notif_msg_tenant_client',
                    'notification_messages', ['tenant_id', 'client_id'])
    op.create_index('idx_notif_msg_created',
                    'notification_messages', ['created_at'])

    # ── Seed default system email template for pending documents ──────────────
    op.execute("""
        INSERT INTO notification_templates (id, tenant_id, channel, name, subject, body, variables, is_active)
        VALUES (
            gen_random_uuid(),
            NULL,
            'email',
            'Documentos Pendentes - Padrão',
            'Documentos pendentes para entrega ao escritório',
            E'Olá {{client_name}},\n\nPassamos por aqui para lembrá-lo(a) de que o seu escritório contábil aguarda os seguintes documentos referentes à competência {{competence_month}}:\n\n{{pending_items}}\n\nPor favor, acesse o portal do cliente para enviar os documentos: {{portal_link}}\n\nQualquer dúvida, entre em contato conosco.\n\nAtenciosamente,\nEquipe {{office_name}}',
            '{"client_name": "Nome completo do cliente", "competence_month": "Mes de competencia (ex: Maio/2026)", "pending_items": "Lista formatada dos documentos pendentes", "portal_link": "Link de acesso ao portal", "office_name": "Nome do escritorio"}',
            true
        )
        ON CONFLICT DO NOTHING;
    """)


def downgrade() -> None:
    op.drop_index('idx_notif_msg_created', table_name='notification_messages')
    op.drop_index('idx_notif_msg_tenant_client', table_name='notification_messages')
    op.drop_index('idx_notif_msg_tenant_status', table_name='notification_messages')
    op.drop_table('notification_messages')
    op.drop_index('idx_notif_tmpl_tenant_channel', table_name='notification_templates')
    op.drop_table('notification_templates')
