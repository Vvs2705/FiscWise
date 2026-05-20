# ContaFlow Backend Dockerfile
# Build context: project root (fly.toml is at root, dockerfile at ./backend/Dockerfile)
# Python 3.12 for compatibility with asyncpg and pydantic-core

FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
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

# Run migrations with retry logic, then start uvicorn.
# Retries alembic up to 10 times (6 s apart) to handle cold-start DB delays
# from Supabase / external Postgres. Total max wait: ~60 s before giving up.
CMD ["sh", "-c", "\
  RETRIES=10; \
  echo \"[startup] Running database migrations (up to $RETRIES attempts)...\"; \
  while [ $RETRIES -gt 0 ]; do \
    python -m alembic upgrade head && break; \
    RETRIES=$((RETRIES - 1)); \
    echo \"[startup] Migration attempt failed. Retries left: $RETRIES. Retrying in 6s...\"; \
    sleep 6; \
  done; \
  if [ $RETRIES -eq 0 ]; then \
    echo '[startup] ERROR: All migration attempts failed. Verify DATABASE_URL secret is set in Fly.io.'; \
    exit 1; \
  fi; \
  echo '[startup] Migrations complete. Starting uvicorn...'; \
  exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1 --log-level info \
"]
