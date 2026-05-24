"""Contract tests for the first safe RLS migration slice."""

from pathlib import Path


def test_rls_context_migration_creates_tenant_function_without_enabling_policies():
    migration = (
        Path(__file__).parents[2]
        / "alembic"
        / "versions"
        / "20260525h_rls_context_function.py"
    )

    sql = migration.read_text(encoding="utf-8")

    assert "CREATE OR REPLACE FUNCTION current_app_tenant_id()" in sql
    assert "current_setting('app.current_tenant_id', true)" in sql
    assert "DROP FUNCTION IF EXISTS current_app_tenant_id()" in sql
    assert "ENABLE ROW LEVEL SECURITY" not in sql
