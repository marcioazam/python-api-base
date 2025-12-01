"""Alembic environment configuration for async SQLAlchemy."""

import asyncio
import importlib
import pkgutil
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from sqlmodel import SQLModel

from my_app.infrastructure.database.alembic_utils import get_database_url


def import_models() -> list[str]:
    """Auto-import all entity models for metadata registration.

    Uses pkgutil to discover and import all modules in the entities package,
    ensuring all SQLModel classes are registered with metadata.

    Returns:
        List of imported module names.

    Raises:
        ImportError: If entities package is not found.
    """
    try:
        import my_app.domain.entities as entities_pkg
    except ImportError as e:
        raise ImportError(
            "Cannot find entities package at my_app.domain.entities. "
            "Ensure the package exists and is properly installed."
        ) from e

    imported_modules: list[str] = []
    for _, module_name, is_pkg in pkgutil.iter_modules(entities_pkg.__path__):
        if not is_pkg and not module_name.startswith("_"):
            full_module_name = f"my_app.domain.entities.{module_name}"
            importlib.import_module(full_module_name)
            imported_modules.append(module_name)

    return imported_modules


# Auto-discover and import all entity models
import_models()

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# SQLModel metadata for autogenerate support
target_metadata = SQLModel.metadata


def _get_url() -> str:
    """Get database URL using config_utils with alembic config."""
    return get_database_url(config)


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = _get_url()
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
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()
    
    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
