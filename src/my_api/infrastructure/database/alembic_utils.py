"""Alembic configuration utilities.

This module contains testable utility functions for Alembic configuration,
extracted from env.py to enable proper unit testing.

**Feature: alembic-migrations-refactoring**
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from alembic.config import Config

# Placeholder patterns that indicate unconfigured database URL
PLACEHOLDER_PATTERNS: tuple[str, ...] = (
    "driver://user:pass@localhost/dbname",
    "postgresql://user:password@localhost/db",
    "postgresql+asyncpg://localhost/placeholder",
)


def is_placeholder_url(url: str) -> bool:
    """Check if URL matches a known placeholder pattern.

    Args:
        url: Database URL to check.

    Returns:
        True if URL is a placeholder, False otherwise.
    """
    return url in PLACEHOLDER_PATTERNS or not url.strip()


def get_database_url(config: Config | None = None) -> str:
    """Get and validate database URL from environment or config.

    Priority order:
    1. DATABASE__URL environment variable
    2. DATABASE_URL environment variable
    3. sqlalchemy.url from alembic.ini (if not a placeholder)

    Args:
        config: Optional Alembic Config object. If None, only env vars are checked.

    Returns:
        Validated database URL string.

    Raises:
        ValueError: If no valid database URL is configured.
    """
    # Try environment variable first (for production/CI)
    url = os.getenv("DATABASE__URL") or os.getenv("DATABASE_URL")
    if url:
        return url

    # Fall back to alembic.ini config
    url = config.get_main_option("sqlalchemy.url", "") if config else ""

    if is_placeholder_url(url):
        raise ValueError(
            "DATABASE_URL not configured. "
            "Set DATABASE__URL or DATABASE_URL environment variable, "
            "or configure a valid sqlalchemy.url in alembic.ini. "
            "Current placeholder values are not valid for database connections."
        )

    return url



def import_models(entities_package: str = "my_api.domain.entities") -> list[str]:
    """Auto-import all entity models for metadata registration.

    Uses pkgutil to discover and import all modules in the entities package,
    ensuring all SQLModel classes are registered with metadata.

    Args:
        entities_package: Fully qualified package name containing entity models.

    Returns:
        List of imported module names.

    Raises:
        ImportError: If entities package is not found.
    """
    import importlib
    import pkgutil

    try:
        entities_pkg = importlib.import_module(entities_package)
    except ImportError as e:
        raise ImportError(
            f"Cannot find entities package at {entities_package}. "
            "Ensure the package exists and is properly installed."
        ) from e

    imported_modules: list[str] = []

    # Get package path - handle both regular packages and namespace packages
    pkg_path = getattr(entities_pkg, "__path__", None)
    if pkg_path is None:
        raise ImportError(
            f"Package {entities_package} has no __path__ attribute. "
            "Ensure it is a proper Python package with __init__.py."
        )

    for _, module_name, is_pkg in pkgutil.iter_modules(pkg_path):
        if not is_pkg and not module_name.startswith("_"):
            full_module_name = f"{entities_package}.{module_name}"
            importlib.import_module(full_module_name)
            imported_modules.append(module_name)

    return imported_modules
