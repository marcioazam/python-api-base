"""Module reloader for hot reload functionality.

**Feature: file-size-compliance-phase2, Task 2.2**
**Validates: Requirements 1.2, 5.1, 5.2, 5.3**
"""

import importlib
import sys
import time
from pathlib import Path
from collections.abc import Callable

from .models import ReloadResult


class ModuleReloader:
    """Handles reloading of Python modules."""

    def __init__(self, base_package: str = "") -> None:
        """Initialize reloader."""
        self._base_package = base_package
        self._reload_callbacks: list[Callable[[list[str]], None]] = []

    def path_to_module(self, path: Path) -> str | None:
        """Convert file path to module name."""
        try:
            if path.suffix != ".py":
                return None

            parts = list(path.with_suffix("").parts)

            if self._base_package:
                try:
                    idx = parts.index(self._base_package.split(".")[0])
                    parts = parts[idx:]
                except ValueError:
                    pass

            module_name = ".".join(parts)

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
                    for attr_value in module.__dict__.values():
                        if hasattr(attr_value, "__module__"):
                            if attr_value.__module__ == module_name:
                                dependents.append(name)
                                break
            except Exception:
                continue
        return dependents
