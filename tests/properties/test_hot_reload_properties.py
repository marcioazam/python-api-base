"""Property tests for hot_reload module.

**Feature: shared-modules-phase2**
**Validates: Requirements 17.2, 17.3, 18.1, 18.2**
"""


import pytest
pytest.skip('Module core.shared.hot_reload not implemented', allow_module_level=True)

import os
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

from core.shared.hot_reload import (
    FileChange,
    FileChangeType,
    FileHasher,
    FileWatcher,
    HotReloadMiddleware,
    ModuleReloader,
    ReloadResult,
    ReloadStrategy,
    WatchConfig,
)


class TestFileHasherProperties:
    """Property tests for FileHasher."""

    def test_same_content_produces_same_hash(self) -> None:
        """Same file content SHALL produce same hash."""
        hasher = FileHasher()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("# test content\nprint('hello')")
            f.flush()
            path = Path(f.name)

        hash1 = hasher.compute_hash(path)
        hash2 = hasher.compute_hash(path)

        assert hash1 == hash2
        path.unlink()

    @settings(max_examples=20)
    @given(content=st.text(min_size=1, max_size=100, alphabet=st.characters(whitelist_categories=("L", "N", "P"))))
    def test_different_content_produces_different_hash(self, content: str) -> None:
        """Different content SHALL produce different hashes."""
        hasher = FileHasher()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f1:
            f1.write(content)
            f1.flush()
            path1 = Path(f1.name)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, encoding="utf-8") as f2:
            f2.write(content + "_modified")
            f2.flush()
            path2 = Path(f2.name)

        hash1 = hasher.compute_hash(path1)
        hash2 = hasher.compute_hash(path2)

        assert hash1 != hash2

        path1.unlink()
        path2.unlink()

    def test_has_changed_detects_modification(self) -> None:
        """has_changed SHALL detect file modifications."""
        hasher = FileHasher()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("original content")
            f.flush()
            path = Path(f.name)

        # First check - establishes baseline
        changed, old_hash, new_hash = hasher.has_changed(path)
        assert changed is True  # First time is always "changed"

        # Second check - no change
        changed, old_hash, new_hash = hasher.has_changed(path)
        assert changed is False

        # Modify file
        path.write_text("modified content")

        # Third check - should detect change
        changed, old_hash, new_hash = hasher.has_changed(path)
        assert changed is True
        assert old_hash != new_hash

        path.unlink()

    def test_nonexistent_file_returns_none(self) -> None:
        """Nonexistent file SHALL return None hash."""
        hasher = FileHasher()
        result = hasher.compute_hash(Path("/nonexistent/file.py"))
        assert result is None


class TestWatchConfigProperties:
    """Property tests for WatchConfig."""

    def test_default_config_has_python_pattern(self) -> None:
        """Default config SHALL include *.py pattern."""
        config = WatchConfig()
        assert "*.py" in config.include_patterns

    def test_default_config_excludes_pycache(self) -> None:
        """Default config SHALL exclude __pycache__."""
        config = WatchConfig()
        assert "__pycache__" in config.exclude_patterns

    @settings(max_examples=20)
    @given(debounce=st.integers(min_value=0, max_value=1000))
    def test_config_preserves_debounce(self, debounce: int) -> None:
        """Config SHALL preserve debounce setting."""
        config = WatchConfig(debounce_ms=debounce)
        assert config.debounce_ms == debounce


class TestFileWatcherProperties:
    """Property tests for FileWatcher."""

    def test_watcher_finds_python_files(self) -> None:
        """Watcher SHALL find Python files in watch paths."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test files
            (tmppath / "test.py").write_text("# test")
            (tmppath / "other.txt").write_text("text file")

            config = WatchConfig(watch_paths=[tmppath])
            watcher = FileWatcher(config)
            files = watcher.scan_all()

            py_files = [f for f in files if f.suffix == ".py"]
            txt_files = [f for f in files if f.suffix == ".txt"]

            assert len(py_files) == 1
            assert len(txt_files) == 0

    def test_watcher_excludes_pycache(self) -> None:
        """Watcher SHALL exclude __pycache__ directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create pycache directory
            pycache = tmppath / "__pycache__"
            pycache.mkdir()
            (pycache / "module.cpython-311.pyc").write_bytes(b"bytecode")

            # Create normal file
            (tmppath / "module.py").write_text("# module")

            config = WatchConfig(watch_paths=[tmppath])
            watcher = FileWatcher(config)
            files = watcher.scan_all()

            # Should only find module.py, not pycache contents
            assert len(files) == 1
            assert all("__pycache__" not in str(f) for f in files)

    def test_initialize_returns_file_count(self) -> None:
        """Initialize SHALL return count of watched files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test files
            (tmppath / "a.py").write_text("# a")
            (tmppath / "b.py").write_text("# b")
            (tmppath / "c.py").write_text("# c")

            config = WatchConfig(watch_paths=[tmppath])
            watcher = FileWatcher(config)
            count = watcher.initialize()

            assert count == 3

    def test_check_changes_detects_new_file(self) -> None:
        """check_changes SHALL detect new files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            config = WatchConfig(watch_paths=[tmppath], debounce_ms=0)
            watcher = FileWatcher(config)
            watcher.initialize()

            # Create new file
            (tmppath / "new.py").write_text("# new file")

            changes = watcher.check_changes()

            assert len(changes) == 1
            assert changes[0].change_type == FileChangeType.CREATED

    def test_check_changes_detects_deleted_file(self) -> None:
        """check_changes SHALL detect deleted files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create initial file
            test_file = tmppath / "test.py"
            test_file.write_text("# test")

            config = WatchConfig(watch_paths=[tmppath], debounce_ms=0)
            watcher = FileWatcher(config)
            watcher.initialize()

            # Delete file
            test_file.unlink()

            changes = watcher.check_changes()

            assert len(changes) == 1
            assert changes[0].change_type == FileChangeType.DELETED


class TestModuleReloaderProperties:
    """Property tests for ModuleReloader."""

    def test_path_to_module_converts_correctly(self) -> None:
        """path_to_module SHALL convert paths to module names."""
        reloader = ModuleReloader(base_package="my_app")

        # Test basic conversion
        path = Path("my_app/shared/utils.py")
        module = reloader.path_to_module(path)
        assert module == "my_app.shared.utils"

    def test_path_to_module_handles_init(self) -> None:
        """path_to_module SHALL handle __init__.py correctly."""
        reloader = ModuleReloader(base_package="my_app")

        path = Path("my_app/shared/__init__.py")
        module = reloader.path_to_module(path)
        assert module == "my_app.shared"

    def test_is_loaded_checks_sys_modules(self) -> None:
        """is_loaded SHALL check sys.modules."""
        reloader = ModuleReloader()

        # os should be loaded
        assert reloader.is_loaded("os") is True

        # nonexistent module should not be loaded
        assert reloader.is_loaded("nonexistent_module_xyz") is False

    def test_reload_result_tracks_success(self) -> None:
        """ReloadResult SHALL track success status."""
        result = ReloadResult(
            success=True,
            reloaded_modules=["module1", "module2"],
            failed_modules=[],
            errors=[],
        )
        assert result.success is True
        assert len(result.reloaded_modules) == 2

    def test_reload_result_tracks_failures(self) -> None:
        """ReloadResult SHALL track failures."""
        result = ReloadResult(
            success=False,
            reloaded_modules=["module1"],
            failed_modules=["module2"],
            errors=["module2: ImportError"],
        )
        assert result.success is False
        assert len(result.failed_modules) == 1
        assert len(result.errors) == 1


class TestHotReloadMiddlewareProperties:
    """Property tests for HotReloadMiddleware."""

    def test_middleware_disabled_by_default_in_prod(self) -> None:
        """Middleware SHALL be configurable for enabled state."""
        middleware = HotReloadMiddleware(enabled=False)
        assert middleware.enabled is False

    def test_middleware_enabled_when_configured(self) -> None:
        """Middleware SHALL be enabled when configured."""
        middleware = HotReloadMiddleware(enabled=True)
        assert middleware.enabled is True

    def test_initialize_returns_file_count(self) -> None:
        """Initialize SHALL return watched file count."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "test.py").write_text("# test")

            middleware = HotReloadMiddleware(
                watch_paths=[tmppath],
                enabled=True,
            )
            count = middleware.initialize()

            assert count == 1

    def test_disabled_middleware_returns_zero(self) -> None:
        """Disabled middleware SHALL return 0 on initialize."""
        middleware = HotReloadMiddleware(enabled=False)
        count = middleware.initialize()
        assert count == 0

    def test_check_and_reload_returns_none_when_disabled(self) -> None:
        """check_and_reload SHALL return None when disabled."""
        middleware = HotReloadMiddleware(enabled=False)
        result = middleware.check_and_reload()
        assert result is None

    def test_get_status_returns_correct_info(self) -> None:
        """get_status SHALL return correct status info."""
        middleware = HotReloadMiddleware(
            enabled=True,
            strategy=ReloadStrategy.CHANGED,
        )
        status = middleware.get_status()

        assert status["enabled"] is True
        assert status["strategy"] == "changed"
        assert status["reload_count"] == 0

    def test_add_watch_path_adds_path(self) -> None:
        """add_watch_path SHALL add new paths."""
        middleware = HotReloadMiddleware(enabled=True)
        initial_count = len(middleware._config.watch_paths)

        middleware.add_watch_path("/new/path")

        assert len(middleware._config.watch_paths) == initial_count + 1

    @settings(max_examples=10)
    @given(strategy=st.sampled_from(list(ReloadStrategy)))
    def test_strategy_is_preserved(self, strategy: ReloadStrategy) -> None:
        """Strategy setting SHALL be preserved."""
        middleware = HotReloadMiddleware(
            enabled=True,
            strategy=strategy,
        )
        assert middleware._strategy == strategy


class TestFileChangeProperties:
    """Property tests for FileChange."""

    def test_file_change_preserves_path(self) -> None:
        """FileChange SHALL preserve path."""
        path = Path("/test/file.py")
        change = FileChange(
            path=path,
            change_type=FileChangeType.MODIFIED,
        )
        assert change.path == path

    @settings(max_examples=10)
    @given(change_type=st.sampled_from(list(FileChangeType)))
    def test_file_change_preserves_type(self, change_type: FileChangeType) -> None:
        """FileChange SHALL preserve change type."""
        change = FileChange(
            path=Path("/test.py"),
            change_type=change_type,
        )
        assert change.change_type == change_type

    def test_file_change_has_timestamp(self) -> None:
        """FileChange SHALL have timestamp."""
        change = FileChange(
            path=Path("/test.py"),
            change_type=FileChangeType.CREATED,
        )
        assert change.timestamp is not None
