"""SSL obrigatório fora do banco local (CI e docker-compose não falam SSL)."""

from app.core.deps import _sanitize_database_url


def test_supabase_exige_ssl():
    url = _sanitize_database_url("postgresql://u:p@db.abc.supabase.co:5432/postgres?sslmode=require")
    assert url.endswith("?ssl=require") and url.startswith("postgresql+asyncpg://")


def test_banco_local_sem_ssl():
    assert "ssl" not in _sanitize_database_url("postgresql://u:p@localhost:5432/fiscwise_test")
    assert "ssl" not in _sanitize_database_url("postgres://u:p@postgres:5432/x")
