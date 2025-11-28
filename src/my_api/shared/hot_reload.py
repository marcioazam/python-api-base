"""Hot Reload Middleware - Automatic code reload in development.

**Feature: api-architecture-analysis, Task 10.5: Hot Reload Middleware**
**Validates: Requirements 10.3**

Provides:
- File system watching for code changes
- Automatic module reloading without server restart
- Configurable watch patterns and ignore patterns
- Development-only middleware with safety checks
"""

import hashlib
import importlib
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class ReloadStrategy(str, Enum):
    """Strategy for reloading modules."""

    FULL = "full"  # Reload all watched modules
    CHANGED = "changed"  # Only reload changed modules
    DEPENDENCY = "dependency"  # Reload changed + dependents


class FileChangeType(str, Enum):
    """Type of file change detected."""

    CREATED = "created"
    MODIFIED = "modified"
    DELETED = "deleted"


@dataclass
class FileChange:
    """Represents a detected file change."""

    path: Path
    change_type: FileChangeType
    timestamp: datetime = field(default_factory=datetime.now)
    old_hash: str | None = None
    new_hash: str | None = None


@dataclass
class WatchConfig:
    """Configuration for file watching."""

    watch_paths: list[Path] = field(default_factory=list)
    include_patterns: list[str] = field(default_factory=lambda: ["*.py"])
    exclude_patterns: list[str] = field(
        default_factory=lambda: ["__pycache__", "*.pyc", ".git", ".venv", "venv"]
    )
    debounce_ms: int = 100
    strategy: ReloadStrategy = ReloadStrategy.CHANGED


@dataclass
class ReloadResult:
    """Result of a reload operation."""

    success: bool
    reloaded_modules: list[str] = field(default_factory=list)
    failed_modules: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)


class FileHasher:
    """Computes and caches file hashes for change detection."""

    def __init__(self) -> None:
        """Initialize hasher."""
        self._cache: dict[Path, str] = {}

    def compute_hash(self, path: Path) -> str | None:
        """Compute MD5 hash of file contents (not for security)."""
        try:
            content = path.read_bytes()
            return hashlib.md5(content, usedforsecurity=False).hexdigest()
        except (OSError, IOError):
            return None

    def has_changed(self, path: Path) -> tuple[bool, str | None, str | None]:
        """Check if file has changed since last check."""
        old_hash = self._cache.get(path)
        new_hash = self.compute_hash(path)

        if new_hash is None:
            # File was deleted
            if old_hash is not None:
                del self._cache[path]
                return True, old_hash, None
            return False, None, None

        if old_hash != new_hash:
            self._cache[path] = new_hash
            return True, old_hash, new_hash

        return False, old_hash, new_hash

    def update_hash(self, path: Path) -> str | None:
        """Update cached hash for a file."""
        new_hash = self.compute_hash(path)
        if new_hash:
            self._cache[path] = new_hash
        return new_hash

    def clear(self) -> None:
        """Clear all cached hashes."""
        self._cache.clear()


class FileWatcher:
    """Watches files for changes."""

    def __init__(self, config: WatchConfig) -> None:
        """Initialize watcher with config."""
        self._config = config
        self._hasher = FileHasher()
        self._known_files: set[Path] = set()
        self._last_check = time.time()

    def _matches_pattern(self, path: Path, patterns: list[str]) -> bool:
        """Check if path matches any of the patterns."""
        name = path.name
        for pattern in patterns:
            if pattern.startswith("*"):
                if name.endswith(pattern[1:]):
                    return True
            elif pattern in str(path):
                return True
            elif name == pattern:
                return True
        return False

    def _should_watch(self, path: Path) -> bool:
        """Determine if a file should be watched."""
        if not path.is_file():
            return False
        if self._matches_pattern(path, self._config.exclude_patterns):
            return False
        if not self._matches_pattern(path, self._config.include_patterns):
            return False
        return True

    def _scan_directory(self, directory: Path) -> set[Path]:
        """Scan directory for watchable files."""
        files: set[Path] = set()
        try:
            for item in directory.rglob("*"):
                if self._should_watch(item):
                    files.add(item)
        except (OSError, PermissionError):
            pass
        return files

    def scan_all(self) -> set[Path]:
        """Scan all watch paths for files."""
        all_files: set[Path] = set()
        for watch_path in self._config.watch_paths:
            if watch_path.is_dir():
                all_files.update(self._scan_directory(watch_path))
            elif watch_path.is_file() and self._should_watch(watch_path):
                all_files.add(watch_path)
        return all_files

    def initialize(self) -> int:
        """Initialize watcher by scanning all files."""
        self._known_files = self.scan_all()
        for file_path in self._known_files:
            self._hasher.update_hash(file_path)
        return len(self._known_files)

    def check_changes(self) -> list[FileChange]:
        """Check for file changes since last check."""
        current_time = time.time()
        if (current_time - self._last_check) * 1000 < self._config.debounce_ms:
            return []

        self._last_check = current_time
        changes: list[FileChange] = []
        current_files = self.scan_all()

        # Check for new files
        new_files = current_files - self._known_files
        for path in new_files:
            new_hash = self._hasher.update_hash(path)
            changes.append(
                FileChange(
                    path=path,
                    change_type=FileChangeType.CREATED,
                    new_hash=new_hash,
                )
            )

        # Check for deleted files
        deleted_files = self._known_files - current_files
        for path in deleted_files:
            changes.append(
                FileChange(
                    path=path,
                    change_type=FileChangeType.DELETED,
                    old_hash=self._hasher._cache.get(path),
                )
            )
            if path in self._hasher._cache:
                del self._hasher._cache[path]

        # Check for modified files
        for path in current_files & self._known_files:
            changed, old_hash, new_hash = self._hasher.has_changed(path)
            if changed:
                changes.append(
                    FileChange(
                        path=path,
                        change_type=FileChangeType.MODIFIED,
                        old_hash=old_hash,
                        new_hash=new_hash,
                    )
                )

        self._known_files = current_files
        return changes


class ModuleReloader:
    """Handles reloading of Python modules."""

    def __init__(self, base_package: str = "") -> None:
        """Initialize reloader."""
        self._base_package = base_package
        self._reload_callbacks: list[Callable[[list[str]], None]] = []

    def path_to_module(self, path: Path) -> str | None:
        """Convert file path to module name."""
        try:
            # Remove .py extension
            if path.suffix != ".py":
                return None

            # Convert path to module notation
            parts = list(path.with_suffix("").parts)

            # Find the package root
            if self._base_package:
                try:
                    idx = parts.index(self._base_package.split(".")[0])
                    parts = parts[idx:]
                except ValueError:
                    pass

            module_name = ".".join(parts)

            # Handle __init__.py
            if module_name.endswith(".__init__"):
                module_name = module_name[:-9]

            return module_name
        except Exception:
            return None

    def is_loaded(self, module_name: str) -> bool:
        """Check if module is currently loaded."""
        return module_name in sys.modules

    def reload_module(self, module_name: str) -> tuple[bool, str | None]:
        """Reload a single module."""
        if module_name not in sys.modules:
            return False, f"Module '{module_name}' not loaded"

        try:
            module = sys.modules[module_name]
            importlib.reload(module)
            return True, None
        except Exception as e:
            return False, str(e)

    def reload_modules(self, module_names: list[str]) -> ReloadResult:
        """Reload multiple modules."""
        start_time = time.time()
        reloaded: list[str] = []
        failed: list[str] = []
        errors: list[str] = []

        for module_name in module_names:
            success, error = self.reload_module(module_name)
            if success:
                reloaded.append(module_name)
            else:
                failed.append(module_name)
                if error:
                    errors.append(f"{module_name}: {error}")

        duration = (time.time() - start_time) * 1000

        # Notify callbacks
        if reloaded:
            for callback in self._reload_callbacks:
                try:
                    callback(reloaded)
                except Exception:
                    pass

        return ReloadResult(
            success=len(failed) == 0,
            reloaded_modules=reloaded,
            failed_modules=failed,
            errors=errors,
            duration_ms=duration,
        )

    def add_reload_callback(self, callback: Callable[[list[str]], None]) -> None:
        """Add callback to be called after reload."""
        self._reload_callbacks.append(callback)

    def get_dependents(self, module_name: str) -> list[str]:
        """Get modules that depend on the given module."""
        dependents: list[str] = []
        for name, module in sys.modules.items():
            if module is None:
                continue
            try:
                if hasattr(module, "__dict__"):
                    for attr_name, attr_value in module.__dict__.items():
                        if hasattr(attr_value, "__module__"):
                            if attr_value.__module__ == module_name:
                                dependents.append(name)
                                break
            except Exception:
                continue
        return dependents


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

        # Convert paths
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

        # Convert changes to module names
        modules_to_reload: list[str] = []
        for change in changes:
            if change.change_type == FileChangeType.DELETED:
                continue
            module_name = self._reloader.path_to_module(change.path)
            if module_name and self._reloader.is_loaded(module_name):
                modules_to_reload.append(module_name)

        if not modules_to_reload:
            return None

        # Apply strategy
        if self._strategy == ReloadStrategy.DEPENDENCY:
            all_modules = set(modules_to_reload)
            for module in modules_to_reload:
                all_modules.update(self._reloader.get_dependents(module))
            modules_to_reload = list(all_modules)

        result = self._reloader.reload_modules(modules_to_reload)
        if result.reloaded_modules:
            self._reload_count += 1
            self._last_reload = datetime.now()

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
    """Factory function to create hot reload middleware.

    Args:
        watch_paths: Paths to watch for changes
        base_package: Base package name for module resolution
        enabled: Whether to enable hot reload (defaults to checking DEBUG env)

    Returns:
        Configured HotReloadMiddleware instance
    """
    import os

    if enabled is None:
        enabled = os.getenv("DEBUG", "false").lower() in ("true", "1", "yes")

    paths = watch_paths or ["src"]

    return HotReloadMiddleware(
        watch_paths=paths,
        base_package=base_package,
        enabled=enabled,
    )
