"""Enable PostgreSQL RLS policies for slice two tables (auth, billing, notifications, and obligations).

Revision ID: 20260525j
Revises: 20260525i
Create Date: 2026-05-25 20:00:00.000000

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = '20260525j'
down_revision = '20260525i'
branch_labels = None
depends_on = None

POLICY_NAME = "tenant_isolation"


def upgrade() -> None:
    # 1. Tables with standard tenant-id isolation
    standard_tables = [
        "client_obligation_profiles",
        "obligation_instances",
        "document_checklist_items",
        "notification_messages",
    ]
    for table in standard_tables:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
        op.execute(
            f"""
            CREATE POLICY {POLICY_NAME} ON "{table}"
            USING (tenant_id = current_app_tenant_id())
            WITH CHECK (tenant_id = current_app_tenant_id())
            """
        )

    # 2. Public-accessible or auth-related tables (require bypass check when current_app_tenant_id() IS NULL)
    public_bypass_tables = [
        "tenants",
        "users",
        "tenant_subscriptions",
        "portal_magic_tokens",
    ]
    for table in public_bypass_tables:
        op.execute(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY')
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
        
        # For 'tenants', the primary key 'id' represents the tenant
        if table == "tenants":
            op.execute(
                f"""
                CREATE POLICY {POLICY_NAME} ON "{table}"
                USING (id = current_app_tenant_id() OR current_app_tenant_id() IS NULL)
                WITH CHECK (id = current_app_tenant_id() OR current_app_tenant_id() IS NULL)
                """
            )
        else:
            op.execute(
                f"""
                CREATE POLICY {POLICY_NAME} ON "{table}"
                USING (tenant_id = current_app_tenant_id() OR current_app_tenant_id() IS NULL)
                WITH CHECK (tenant_id = current_app_tenant_id() OR current_app_tenant_id() IS NULL)
                """
            )

    # 3. Notification templates (allow templates where tenant_id is NULL as global templates)
    op.execute('ALTER TABLE "notification_templates" ENABLE ROW LEVEL SECURITY')
    op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "notification_templates"')
    op.execute(
        f"""
        CREATE POLICY {POLICY_NAME} ON "notification_templates"
        USING (tenant_id = current_app_tenant_id() OR tenant_id IS NULL)
        WITH CHECK (tenant_id = current_app_tenant_id() OR tenant_id IS NULL)
        """
    )


def downgrade() -> None:
    # Disable RLS and drop policies for notification_templates
    op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "notification_templates"')
    op.execute('ALTER TABLE "notification_templates" DISABLE ROW LEVEL SECURITY')

    # Disable RLS and drop policies for public_bypass_tables
    public_bypass_tables = [
        "portal_magic_tokens",
        "tenant_subscriptions",
        "users",
        "tenants",
    ]
    for table in public_bypass_tables:
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')

    # Disable RLS and drop policies for standard_tables
    standard_tables = [
        "notification_messages",
        "document_checklist_items",
        "obligation_instances",
        "client_obligation_profiles",
    ]
    for table in standard_tables:
        op.execute(f'DROP POLICY IF EXISTS {POLICY_NAME} ON "{table}"')
        op.execute(f'ALTER TABLE "{table}" DISABLE ROW LEVEL SECURITY')
