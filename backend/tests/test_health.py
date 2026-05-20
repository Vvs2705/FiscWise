"""Smoke tests for app import and basic configuration."""


def test_imports():
    """All critical modules import without errors."""
    from app.core.config import settings
    from app.core.security import JWT_SECRET_KEY
    from app.main import app
    from app.schemas.token import AuthResponse, UserInfo

    assert app.title == "ContaFlow API"
    assert settings.APP_NAME == "ContaFlow"
    assert JWT_SECRET_KEY is not None
    assert AuthResponse is not None
    assert UserInfo is not None


def test_config_environment():
    """Settings load correctly."""
    from app.core.config import settings

    assert settings.CHUNK_SIZE == 1000
    assert settings.TOP_K_RESULTS == 5


def test_root_health_endpoint_returns_online_status(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ContaFlow API Online"}
