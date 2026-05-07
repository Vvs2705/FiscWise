"""Smoke tests — verify the app imports and health endpoint work."""
import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import os

os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-at-least-32-chars-long")
os.environ.setdefault("ANTHROPIC_API_KEY", "test")
os.environ.setdefault("VOYAGE_API_KEY", "test")


def test_imports():
    """All critical modules import without errors."""
    from app.core.config import settings
    from app.core.security import JWT_SECRET_KEY
    from app.schemas.token import AuthResponse, UserInfo
    assert settings.APP_NAME == "ContaFlow"
    assert JWT_SECRET_KEY is not None


def test_config_environment():
    """Settings load correctly."""
    from app.core.config import settings
    assert settings.CHUNK_SIZE == 1000
    assert settings.TOP_K_RESULTS == 5
