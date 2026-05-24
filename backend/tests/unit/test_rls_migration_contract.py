"""Contract tests for the safe RLS migration slices."""

import importlib.util
from pathlib import Path
from types import ModuleType


VERSIONS_DIR = Path(__file__).parents[2] / "alembic" / "versions"

RLS_ENABLED_TENANT_TABLES = {
    "account_receivables",
    "accounting_clients",
    "audit_events",
    "calculator_simulations",
    "client_documents",
    "company_documents",
    "company_partners",
    "das_payments",
    "deadline_items",
    "digital_certificates",
    "fiscal_assistant_messages",
    "tax_scenarios",
}

DEFERRED_OR_GLOBAL_TABLES = {
    "billing_webhook_events",
    "client_obligation_profiles",
    "client_portal_invites",
    "document_checklist_items",
    "fiscal_benefits",
    "notification_templates",
    "notification_messages",
    "obligation_instances",
    "obligation_rules",
    "plans",
    "portal_magic_tokens",
    "tenants",
    "tenant_subscriptions",
    "users",
}


def _load_migration(filename: str) -> ModuleType:
    migration_path = VERSIONS_DIR / filename
    spec = importlib.util.spec_from_file_location(migration_path.stem, migration_path)
    assert spec is not None
    assert spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    return migration


def test_rls_context_migration_creates_tenant_function_without_enabling_policies():
    migration = VERSIONS_DIR / "20260525h_rls_context_function.py"

    sql = migration.read_text(encoding="utf-8")

    assert "CREATE OR REPLACE FUNCTION current_app_tenant_id()" in sql
    assert "current_setting('app.current_tenant_id', true)" in sql
    assert "DROP FUNCTION IF EXISTS current_app_tenant_id()" in sql
    assert "ENABLE ROW LEVEL SECURITY" not in sql


def test_tenant_rls_migration_covers_only_publishable_table_slice(monkeypatch):
    migration = _load_migration("20260525i_enable_tenant_rls_policies.py")

    assert set(migration.RLS_ENABLED_TENANT_TABLES) == RLS_ENABLED_TENANT_TABLES
    assert set(migration.RLS_ENABLED_TENANT_TABLES).isdisjoint(DEFERRED_OR_GLOBAL_TABLES)

    statements: list[str] = []
    monkeypatch.setattr(migration.op, "execute", statements.append)

    migration.upgrade()
    sql = "\n".join(statements)

    assert "FORCE ROW LEVEL SECURITY" not in sql

    for table in RLS_ENABLED_TENANT_TABLES:
        quoted_table = f'"{table}"'
        assert f"ALTER TABLE {quoted_table} ENABLE ROW LEVEL SECURITY" in sql
        assert f"DROP POLICY IF EXISTS tenant_isolation ON {quoted_table}" in sql
        assert f"CREATE POLICY tenant_isolation ON {quoted_table}" in sql
        assert "tenant_id = current_app_tenant_id()" in sql
        assert "WITH CHECK (tenant_id = current_app_tenant_id())" in sql

    for table in DEFERRED_OR_GLOBAL_TABLES:
        assert f'"{table}"' not in sql
