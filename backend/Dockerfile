# ContaFlow Backend Dockerfile
# Build context: project root (fly.toml is at root, dockerfile at ./backend/Dockerfile)
# Python 3.12 for compatibility with asyncpg, psycopg, and pydantic-core

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
# gcc is needed for C extensions (asyncpg, pydantic-core).
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
# Path is relative to build context (project root)
COPY backend/requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# Copy application code from backend/ subdirectory into WORKDIR
COPY backend/ .

# Expose port
EXPOSE 8000

# Health check — start-period gives time for migrations + uvicorn boot
HEALTHCHECK --interval=15s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Startup strategy:
#   1. run_migrations.py runs Alembic upgrade head.
#      The 20260520_fix_enum_case migration handles enum case conversion if needed.
#      If enum issues arise post-deploy, use POST /api/v1/admin/fix-enum-case.
#   2. Uvicorn starts REGARDLESS of migration outcome so the Fly.io
#      health-check (/api/v1/health) can pass even when DATABASE_URL is not
#      yet configured.
CMD ["sh", "-c", "\
  echo '[startup] Running database migrations (with enum preflight fix)...'; \
  RETRIES=10; \
  MIGRATION_OK=0; \
  while [ $RETRIES -gt 0 ]; do \
    if python run_migrations.py; then \
      MIGRATION_OK=1; \
      break; \
    fi; \
    RETRIES=$((RETRIES - 1)); \
    echo \"[startup] Migration attempt failed. Retries left: $RETRIES. Retrying in 6s...\"; \
    sleep 6; \
  done; \
  if [ $MIGRATION_OK -eq 0 ]; then \
    echo '[startup] WARNING: All migration attempts failed.'; \
    echo '[startup] Verify DATABASE_URL secret is set: flyctl secrets set DATABASE_URL=<url>'; \
    echo '[startup] Starting uvicorn anyway so health-check can pass...'; \
  else \
    echo '[startup] Migrations complete.'; \
  fi; \
  echo '[startup] Starting uvicorn...'; \
  exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info \
"]
