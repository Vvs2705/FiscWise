"""
Alembic Environment Configuration for ContaFlow

This module configures Alembic to work with SQLAlchemy 2.0 Async.
It handles both online (connected to database) and offline (SQL script generation) modes.
"""

import asyncio
import os
from logging.config import fileConfig
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

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

# Load DATABASE_URL from environment variable
# This allows us to keep credentials out of alembic.ini
def _sanitize_database_url(url: str) -> str:
    """Convert DATABASE_URL to asyncpg-compatible format.

    Handles Supabase URLs that include sslmode parameter, which asyncpg doesn't support.
    Converts postgres:// to postgresql+asyncpg:// and replaces sslmode with ssl param.
    """
    parsed = urlparse(url)

    # Ensure asyncpg scheme
    if parsed.scheme == "postgres":
        parsed = parsed._replace(scheme="postgresql+asyncpg")
    elif parsed.scheme == "postgresql" and "+asyncpg" not in parsed.scheme:
        parsed = parsed._replace(scheme="postgresql+asyncpg")

    # Parse and fix query parameters
    params = parse_qs(parsed.query, keep_blank_values=True)

    # Remove sslmode (asyncpg doesn't support it)
    if "sslmode" in params:
        del params["sslmode"]

    # Add asyncpg-compatible SSL params
    params["ssl"] = ["require"]
    params["statement_cache_size"] = ["0"]

    # Rebuild query string
    new_query = urlencode(params, doseq=True)

    # Rebuild URL
    fixed_url = urlunparse((
        parsed.scheme,
        parsed.netloc,
        parsed.path,
        parsed.params,
        new_query,
        parsed.fragment
    ))

    return fixed_url


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
    return _sanitize_database_url(database_url)


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
