"""enable_rls_on_client_portal_invites

Revision ID: 20260525p
Revises: 20260525o
Create Date: 2026-05-25 23:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20260525p'
down_revision: Union[str, None] = '20260525o'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

POLICY_NAME = "tenant_isolation"


def upgrade() -> None:
    table = "client_portal_invites"
    op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
    op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
    op.execute(
        f"""
        CREATE POLICY {POLICY_NAME} ON "{table}"
        USING (tenant_id = current_app_tenant_id() OR current_app_tenant_id() IS NULL)
        WITH CHECK (tenant_id = current_app_tenant_id() OR current_app_tenant_id() IS NULL)
        """
    )


def downgrade() -> None:
    table = "client_portal_invites"
    op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
    op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
