"""Hot reload middleware for development.

**Feature: file-size-compliance-phase2, Task 2.2**
**Validates: Requirements 1.2, 5.1, 5.2, 5.3**
"""

import os
from datetime import datetime, UTC
from pathlib import Path
from typing import Any
from collections.abc import Callable

from .enums import FileChangeType, ReloadStrategy
from .handler import ModuleReloader
from .models import ReloadResult, WatchConfig
from .watcher import FileWatcher


class HotReloadMiddleware:
    """Middleware for hot reloading in development."""

    def __init__(
        self,
        watch_paths: list[str | Path] | None = None,
        base_package: str = "",
        enabled: bool = True,
        strategy: ReloadStrategy = ReloadStrategy.CHANGED,
    ) -> None:
        """Initialize hot reload middleware."""
        self._enabled = enabled
        self._strategy = strategy

        paths = [Path(p) if isinstance(p, str) else p for p in (watch_paths or [])]

        self._config = WatchConfig(
            watch_paths=paths,
            strategy=strategy,
        )
        self._watcher = FileWatcher(self._config)
        self._reloader = ModuleReloader(base_package)
        self._initialized = False
        self._reload_count = 0
        self._last_reload: datetime | None = None

    def initialize(self) -> int:
        """Initialize the middleware."""
        if not self._enabled:
            return 0
        count = self._watcher.initialize()
        self._initialized = True
        return count

    def check_and_reload(self) -> ReloadResult | None:
        """Check for changes and reload if necessary."""
        if not self._enabled or not self._initialized:
            return None

        changes = self._watcher.check_changes()
        if not changes:
            return None

        modules_to_reload: list[str] = []
        for change in changes:
            if change.change_type == FileChangeType.DELETED:
                continue
            module_name = self._reloader.path_to_module(change.path)
            if module_name and self._reloader.is_loaded(module_name):
                modules_to_reload.append(module_name)

        if not modules_to_reload:
            return None

        if self._strategy == ReloadStrategy.DEPENDENCY:
            all_modules = set(modules_to_reload)
            for module in modules_to_reload:
                all_modules.update(self._reloader.get_dependents(module))
            modules_to_reload = list(all_modules)

        result = self._reloader.reload_modules(modules_to_reload)
        if result.reloaded_modules:
            self._reload_count += 1
            self._last_reload = datetime.now(UTC)

        return result

    @property
    def enabled(self) -> bool:
        """Check if hot reload is enabled."""
        return self._enabled

    @property
    def reload_count(self) -> int:
        """Get total number of reloads performed."""
        return self._reload_count

    @property
    def last_reload(self) -> datetime | None:
        """Get timestamp of last reload."""
        return self._last_reload

    def add_watch_path(self, path: str | Path) -> None:
        """Add a path to watch."""
        p = Path(path) if isinstance(path, str) else path
        if p not in self._config.watch_paths:
            self._config.watch_paths.append(p)

    def add_reload_callback(self, callback: Callable[[list[str]], None]) -> None:
        """Add callback for reload events."""
        self._reloader.add_reload_callback(callback)

    def get_watched_files(self) -> list[Path]:
        """Get list of currently watched files."""
        return list(self._watcher._known_files)

    def get_status(self) -> dict[str, Any]:
        """Get current status of hot reload."""
        return {
            "enabled": self._enabled,
            "initialized": self._initialized,
            "strategy": self._strategy.value,
            "watched_files": len(self._watcher._known_files),
            "reload_count": self._reload_count,
            "last_reload": self._last_reload.isoformat() if self._last_reload else None,
        }


def create_hot_reload_middleware(
    watch_paths: list[str] | None = None,
    base_package: str = "my_api",
    enabled: bool | None = None,
) -> HotReloadMiddleware:
    """Factory function to create hot reload middleware."""
    if enabled is None:
        enabled = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    paths = watch_paths or ["src"]

    return HotReloadMiddleware(
        watch_paths=paths,
        base_package=base_package,
        enabled=enabled,
    )
