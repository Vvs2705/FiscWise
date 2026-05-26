# FiscWise Backend Dockerfile
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

# Run as non-root user for security hardening
RUN addgroup --system --gid 1001 appgroup && \
    adduser --system --uid 1001 --ingroup appgroup --no-create-home appuser && \
    chown -R appuser:appgroup /app
USER appuser

# Expose port
EXPOSE 8000

# Health check — start-period gives time for migrations + uvicorn boot
HEALTHCHECK --interval=15s --timeout=10s --start-period=120s --retries=5 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Startup: uvicorn starts immediately.
# Database migrations are run via Fly.io release_command (fly.toml [deploy])
# BEFORE this container starts, so the port is available instantly and
# the "app not listening" smoke-check warning is eliminated.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--log-level", "info"]
