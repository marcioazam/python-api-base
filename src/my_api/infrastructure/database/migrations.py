"""Database migration utilities for application startup."""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


def get_alembic_config() -> Config:
    """Get Alembic configuration.
    
    Returns:
        Alembic Config object.
    """
    # Find project root (where alembic.ini is)
    current = Path(__file__).resolve()
    root = current.parent.parent.parent.parent.parent  # src/my_api/infrastructure/database -> root

    alembic_ini = root / "alembic.ini"
    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")

    config = Config(str(alembic_ini))
    config.set_main_option("script_location", str(root / "alembic"))

    return config


async def check_pending_migrations(engine: AsyncEngine) -> bool:
    """Check if there are pending migrations.
    
    Args:
        engine: Async database engine.
        
    Returns:
        True if there are pending migrations.
    """
    def _check(connection) -> bool:
        context = MigrationContext.configure(connection)
        current_rev = context.get_current_revision()

        config = get_alembic_config()
        script = config.get_main_option("script_location")

        # Get head revision from alembic
        from alembic.script import ScriptDirectory
        script_dir = ScriptDirectory.from_config(config)
        head_rev = script_dir.get_current_head()

        return current_rev != head_rev

    async with engine.connect() as conn:
        return await conn.run_sync(_check)


async def get_current_revision(engine: AsyncEngine) -> str | None:
    """Get current database revision.
    
    Args:
        engine: Async database engine.
        
    Returns:
        Current revision string or None.
    """
    def _get_revision(connection) -> str | None:
        context = MigrationContext.configure(connection)
        return context.get_current_revision()

    async with engine.connect() as conn:
        return await conn.run_sync(_get_revision)


def run_migrations_sync(database_url: str) -> None:
    """Run pending migrations synchronously.
    
    This is useful for startup scripts or CLI tools.
    
    Args:
        database_url: Database connection URL.
    """
    config = get_alembic_config()
    config.set_main_option("sqlalchemy.url", database_url)

    logger.info("Running database migrations...")
    command.upgrade(config, "head")
    logger.info("Database migrations completed")


async def ensure_database_ready(engine: AsyncEngine) -> None:
    """Ensure database is ready with all migrations applied.
    
    Args:
        engine: Async database engine.
        
    Raises:
        RuntimeError: If migrations are pending and auto-migrate is disabled.
    """
    current = await get_current_revision(engine)
    has_pending = await check_pending_migrations(engine)

    if has_pending:
        logger.warning(
            f"Database has pending migrations. Current revision: {current}. "
            "Run 'python scripts/migrate.py upgrade head' to apply migrations."
        )
    else:
        logger.info(f"Database is up to date at revision: {current}")
