"""Produção não sobe com JWT_SECRET_KEY curto ou de exemplo (SEC-6)."""

from app.core.config import settings
from app.main import weak_production_secrets


def test_jwt_fraco_em_producao(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(
        settings, "JWT_SECRET_KEY", "dev_secret_key_do_not_use_in_production"
    )
    assert weak_production_secrets()
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "curto")
    assert weak_production_secrets()


def test_jwt_forte_em_producao(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "a3f9" * 32)
    assert weak_production_secrets() == []


def test_dev_nao_bloqueia(monkeypatch):
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "JWT_SECRET_KEY", "curto")
    assert weak_production_secrets() == []
