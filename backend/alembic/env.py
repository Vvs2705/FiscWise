"""
Alembic Environment Configuration for ContaFlow

This module configures Alembic to work with SQLAlchemy 2.0 Async.
It handles both online (connected to database) and offline (SQL script generation) modes.
"""

import asyncio
import os
import re
import logging
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

logger = logging.getLogger(__name__)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
# Import all models to ensure they are registered with SQLAlchemy
from app.models import Base

# Set target_metadata to Base.metadata for autogenerate support
target_metadata = Base.metadata


def _sanitize_database_url(url: str) -> str:
    """Convert DATABASE_URL to asyncpg-compatible format using regex.

    Uses regex instead of urlparse/urlunparse to avoid corruption of
    URL-encoded characters in passwords (e.g. %23 for #, %40 for @).

    - Normalises scheme to postgresql+asyncpg://
    - Strips ?sslmode param (asyncpg uses ?ssl= instead)
    - Adds ?ssl=require&statement_cache_size=0 (required for Supabase/PgBouncer)
    """
    # Normalise scheme: postgres:// or postgresql:// → postgresql+asyncpg://
    # Also handles postgresql+asyncpg:// (no-op) and postgresql+psycopg2:// etc.
    url = re.sub(r'^postgres(?:ql)?(?:\+\w+)?://', 'postgresql+asyncpg://', url)

    # Strip query string entirely and rebuild it cleanly
    # Split on '?' to separate base URL from query params
    if '?' in url:
        base, qs = url.split('?', 1)
        # Remove sslmode param; keep everything else (except ssl= which we re-add)
        params = []
        for part in qs.split('&'):
            if part.startswith('sslmode=') or part.startswith('ssl=') or part == 'sslmode' or part == 'ssl':
                continue
            if part:
                params.append(part)
    else:
        base = url
        params = []

    params.append('ssl=require')
    params.append('statement_cache_size=0')

    return f"{base}?{'&'.join(params)}"


def get_url():
    """
    Get database URL from environment variable.

    Ensures the URL uses the asyncpg driver required by SQLAlchemy async.
    Supabase URLs contain sslmode parameter which must be replaced with
    asyncpg-compatible ssl and statement_cache_size parameters.

    Returns:
        str: Database connection URL with asyncpg driver specifier
    """
    database_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://contaflow:contaflow_dev_2026@localhost:5432/contaflow_db"
    )
    logger.info(f"DATABASE_URL loaded from environment: {database_url[:50]}...")
    try:
        sanitized = _sanitize_database_url(database_url)
        logger.info(f"Sanitized URL: {sanitized[:50]}...")
        return sanitized
    except Exception as e:
        logger.error(f"Error sanitizing DATABASE_URL: {e}", exc_info=True)
        raise


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """
    Execute migrations with the given connection.
    
    Args:
        connection: SQLAlchemy connection object
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using async engine.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_url()
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.
    
    This is the entry point for async migrations.
    """
    asyncio.run(run_async_migrations())


# Determine which mode to run
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
