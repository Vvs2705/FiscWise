"""Add is_superuser to users table

Revision ID: 20260526b
Revises: 20260526a
Create Date: 2026-05-26 12:00:00.000000

Replaces static ADMIN_EMERGENCY_TOKEN with RBAC-based superuser flag.
Set is_superuser=true directly via SQL for platform admins:
  UPDATE users SET is_superuser = true WHERE email = 'admin@fiscwise.com.br';
"""
from alembic import op
import sqlalchemy as sa

revision = '20260526b'
down_revision = '20260526a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'is_superuser',
            sa.Boolean(),
            nullable=False,
            server_default='false',
            comment='Cross-tenant superuser access for platform administration',
        ),
    )
    op.create_index('ix_users_is_superuser', 'users', ['is_superuser'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_users_is_superuser', table_name='users')
    op.drop_column('users', 'is_superuser')
