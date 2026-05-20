"""Minimal conftest for unit tests (no FastAPI/Alembic dependencies)."""

import os
import pytest

# Set minimal environment variables for unit tests
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-for-ci-at-least-32-chars-long")
