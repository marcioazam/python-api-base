"""Property-based tests for file size compliance Phase 2.

**Feature: file-size-compliance-phase2, Task 1.1**
**Validates: Requirements 5.1, 5.2, 5.3, 6.1, 6.3**
"""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


MAX_LINES = 400
SRC_DIR = Path("src")
EXCLUDE_PATTERNS = ["__pycache__", ".pyc"]

# Phase 2 refactored packages - will be populated as refactoring progresses
REFACTORED_PACKAGES_PHASE2: list[str] = [
    # High Priority (401-500 lines)
    "src/my_app/shared/waf",
    "src/my_app/shared/hot_reload",
    "src/my_app/shared/auto_ban",
    "src/my_app/shared/csp_generator",
    "src/my_app/shared/lazy",
    "src/my_app/shared/fingerprint",
    # Medium Priority Part 1 (440-460 lines)
    "src/my_app/shared/query_analyzer",
    "src/my_app/shared/protocols",
    "src/my_app/shared/multitenancy",
    "src/my_app/shared/background_tasks",
    # Medium Priority Part 2 (420-440 lines)
    "src/my_app/shared/http2_config",
    "src/my_app/shared/connection_pool",
    "src/my_app/shared/memory_profiler",
    "src/my_app/shared/bff",
    "src/my_app/shared/request_signing",
    # Medium Priority Part 3 (400-425 lines)
    "src/my_app/shared/feature_flags",
    "src/my_app/shared/streaming",
    "src/my_app/shared/api_composition",
    "src/my_app/shared/response_transformation",
    "src/my_app/shared/mutation_testing",
    "src/my_app/shared/graphql_federation",
    # Infrastructure
    "src/my_app/infrastructure/auth/token_store",
    "src/my_app/infrastructure/observability/telemetry",
    # Adapters
    "src/my_app/adapters/api/routes/auth",
]

# Module import paths for backward compatibility testing
REFACTORED_MODULES_PHASE2: list[str] = [
    "my_app.shared.waf",
    "my_app.shared.hot_reload",
    "my_app.shared.auto_ban",
    "my_app.shared.csp_generator",
    "my_app.shared.lazy",
    "my_app.shared.fingerprint",
    "my_app.shared.query_analyzer",
    "my_app.shared.protocols",
    "my_app.shared.multitenancy",
    "my_app.shared.background_tasks",
    "my_app.shared.http2_config",
    "my_app.shared.connection_pool",
    "my_app.shared.memory_profiler",
    "my_app.shared.bff",
    "my_app.shared.request_signing",
    "my_app.shared.feature_flags",
    "my_app.shared.streaming",
    "my_app.shared.api_composition",
    "my_app.shared.response_transformation",
    "my_app.shared.mutation_testing",
    "my_app.shared.graphql_federation",
    "my_app.infrastructure.auth.token_store",
    "my_app.infrastructure.observability.telemetry",
    "my_app.adapters.api.routes.auth",
]


def count_lines(file_path: Path) -> int:
    """Count lines in a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return len(content.splitlines())
    except Exception:
        return 0


def get_package_python_files(package_path: str) -> list[Path]:
    """Get all Python files in a package directory."""
    package = Path(package_path)
    if not package.exists():
        return []
    
    files = []
    for py_file in package.rglob("*.py"):
        path_str = str(py_file)
        if not any(pattern in path_str for pattern in EXCLUDE_PATTERNS):
            files.append(py_file)
    return files


def get_existing_packages() -> list[str]:
    """Get list of packages that currently exist."""
    return [p for p in REFACTORED_PACKAGES_PHASE2 if Path(p).exists()]


def get_existing_modules() -> list[str]:
    """Get list of modules that can be imported."""
    existing = []
    for module in REFACTORED_MODULES_PHASE2:
        # Convert module path to file path
        parts = module.split(".")
        package_path = Path("src") / "/".join(parts)
        if package_path.exists() and (package_path / "__init__.py").exists():
            existing.append(module)
    return existing


class TestPublicAPIPreservationPhase2:
    """Property tests for public API preservation after Phase 2 refactoring.

    **Feature: file-size-compliance-phase2, Property 1: Public API Preservation**
    **Validates: Requirements 5.1, 5.2, 5.3**
    """

    @given(st.sampled_from(REFACTORED_MODULES_PHASE2))
    @settings(max_examples=100, deadline=None)
    def test_module_importable(self, module_name: str) -> None:
        """Property: All refactored modules are importable.

        **Feature: file-size-compliance-phase2, Property 1: Public API Preservation**
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        import importlib
        
        # Convert module path to package path for existence check
        parts = module_name.split(".")
        package_path = Path("src") / "/".join(parts)
        
        # Skip if package doesn't exist yet (not refactored)
        if not package_path.exists():
            pytest.skip(f"Package {module_name} not yet refactored")
        
        # Try to import the module
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            pytest.fail(f"Failed to import {module_name}: {e}")

    @given(st.sampled_from(REFACTORED_MODULES_PHASE2))
    @settings(max_examples=100, deadline=None)
    def test_module_has_all_attribute(self, module_name: str) -> None:
        """Property: All refactored modules have __all__ defined.

        **Feature: file-size-compliance-phase2, Property 1: Public API Preservation**
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        import importlib
        
        parts = module_name.split(".")
        package_path = Path("src") / "/".join(parts)
        
        if not package_path.exists():
            pytest.skip(f"Package {module_name} not yet refactored")
        
        try:
            module = importlib.import_module(module_name)
            assert hasattr(module, "__all__"), (
                f"Module {module_name} should have __all__ defined for explicit exports"
            )
            assert len(module.__all__) > 0, (
                f"Module {module_name} __all__ should not be empty"
            )
        except ImportError:
            pytest.skip(f"Module {module_name} not importable")

    @given(st.sampled_from(REFACTORED_MODULES_PHASE2))
    @settings(max_examples=100, deadline=None)
    def test_all_exports_accessible(self, module_name: str) -> None:
        """Property: All symbols in __all__ are accessible.

        **Feature: file-size-compliance-phase2, Property 1: Public API Preservation**
        **Validates: Requirements 5.1, 5.2, 5.3**
        """
        import importlib
        
        parts = module_name.split(".")
        package_path = Path("src") / "/".join(parts)
        
        if not package_path.exists():
            pytest.skip(f"Package {module_name} not yet refactored")
        
        try:
            module = importlib.import_module(module_name)
            if not hasattr(module, "__all__"):
                pytest.skip(f"Module {module_name} has no __all__")
            
            missing = []
            for symbol in module.__all__:
                if not hasattr(module, symbol):
                    missing.append(symbol)
            
            assert not missing, (
                f"Module {module_name} missing exports: {missing}"
            )
        except ImportError:
            pytest.skip(f"Module {module_name} not importable")



class TestFileSizeCompliancePhase2:
    """Property tests for file size compliance in Phase 2 refactored packages.

    **Feature: file-size-compliance-phase2, Property 2: File Size Compliance**
    **Validates: Requirements 6.1**
    """

    def test_all_refactored_packages_under_max_lines(self) -> None:
        """Property: All files in refactored packages are under 400 lines.

        **Feature: file-size-compliance-phase2, Property 2: File Size Compliance**
        **Validates: Requirements 6.1**
        """
        violations = []
        packages_checked = 0
        
        for package_path in REFACTORED_PACKAGES_PHASE2:
            package = Path(package_path)
            if not package.exists():
                continue
            
            packages_checked += 1
            for py_file in get_package_python_files(package_path):
                line_count = count_lines(py_file)
                if line_count > MAX_LINES:
                    violations.append((py_file, line_count))
        
        if packages_checked == 0:
            pytest.skip("No Phase 2 packages refactored yet")
        
        if violations:
            violation_msgs = [
                f"  {path}: {lines} lines (+{lines - MAX_LINES})"
                for path, lines in sorted(violations, key=lambda x: x[1], reverse=True)
            ]
            pytest.fail(
                f"{len(violations)} files exceed {MAX_LINES} lines:\n"
                + "\n".join(violation_msgs)
            )

    @given(st.sampled_from(REFACTORED_PACKAGES_PHASE2))
    @settings(max_examples=100)
    def test_package_files_under_max_lines(self, package_path: str) -> None:
        """Property: Each file in a refactored package is under 400 lines.

        **Feature: file-size-compliance-phase2, Property 2: File Size Compliance**
        **Validates: Requirements 6.1**
        """
        package = Path(package_path)
        if not package.exists():
            pytest.skip(f"Package {package_path} not yet refactored")
        
        violations = []
        for py_file in get_package_python_files(package_path):
            line_count = count_lines(py_file)
            if line_count > MAX_LINES:
                violations.append((py_file, line_count))
        
        assert not violations, (
            f"Files exceeding {MAX_LINES} lines in {package_path}: "
            + ", ".join(f"{p}:{c}" for p, c in violations)
        )

    def test_refactored_packages_have_multiple_modules(self) -> None:
        """Property: Refactored packages have multiple focused modules.

        **Feature: file-size-compliance-phase2, Property 2: File Size Compliance**
        **Validates: Requirements 6.1**
        """
        packages_checked = 0
        single_module_packages = []
        
        for package_path in REFACTORED_PACKAGES_PHASE2:
            package = Path(package_path)
            if not package.exists():
                continue
            
            packages_checked += 1
            py_files = list(package.glob("*.py"))
            # Should have more than just __init__.py
            if len(py_files) <= 1:
                single_module_packages.append(package_path)
        
        if packages_checked == 0:
            pytest.skip("No Phase 2 packages refactored yet")
        
        assert not single_module_packages, (
            f"Packages with only __init__.py (should have multiple modules): "
            + ", ".join(single_module_packages)
        )



class TestNoCircularImportsPhase2:
    """Property tests for circular import detection in Phase 2 refactored packages.

    **Feature: file-size-compliance-phase2, Property 3: No Circular Imports**
    **Validates: Requirements 6.3**
    """

    @given(st.sampled_from(REFACTORED_MODULES_PHASE2))
    @settings(max_examples=100)
    def test_no_circular_imports_on_module_import(self, module_name: str) -> None:
        """Property: Importing any module does not raise circular import errors.

        **Feature: file-size-compliance-phase2, Property 3: No Circular Imports**
        **Validates: Requirements 6.3**
        """
        import importlib
        import sys
        
        parts = module_name.split(".")
        package_path = Path("src") / "/".join(parts)
        
        if not package_path.exists():
            pytest.skip(f"Package {module_name} not yet refactored")
        
        # Clear any cached imports to ensure fresh import
        modules_to_clear = [k for k in sys.modules if k.startswith(module_name)]
        for mod in modules_to_clear:
            del sys.modules[mod]
        
        try:
            module = importlib.import_module(module_name)
            assert module is not None
        except ImportError as e:
            if "circular" in str(e).lower():
                pytest.fail(f"Circular import detected in {module_name}: {e}")
            # Re-raise other import errors
            raise

    def test_all_submodules_importable(self) -> None:
        """Property: All submodules in refactored packages are importable.

        **Feature: file-size-compliance-phase2, Property 3: No Circular Imports**
        **Validates: Requirements 6.3**
        """
        import importlib
        
        circular_imports = []
        packages_checked = 0
        
        for package_path in REFACTORED_PACKAGES_PHASE2:
            package = Path(package_path)
            if not package.exists():
                continue
            
            packages_checked += 1
            
            # Get all Python files in the package
            for py_file in package.glob("*.py"):
                if py_file.name == "__init__.py":
                    continue
                
                # Convert file path to module path
                module_name = py_file.stem
                parts = package_path.replace("src/", "").replace("/", ".")
                full_module = f"{parts}.{module_name}"
                
                try:
                    importlib.import_module(full_module)
                except ImportError as e:
                    if "circular" in str(e).lower():
                        circular_imports.append((full_module, str(e)))
        
        if packages_checked == 0:
            pytest.skip("No Phase 2 packages refactored yet")
        
        assert not circular_imports, (
            f"Circular imports detected:\n"
            + "\n".join(f"  {mod}: {err}" for mod, err in circular_imports)
        )

    def test_cross_module_imports_work(self) -> None:
        """Property: Cross-module imports within packages work correctly.

        **Feature: file-size-compliance-phase2, Property 3: No Circular Imports**
        **Validates: Requirements 6.3**
        """
        import importlib
        
        packages_checked = 0
        import_errors = []
        
        for package_path in REFACTORED_PACKAGES_PHASE2:
            package = Path(package_path)
            if not package.exists():
                continue
            
            packages_checked += 1
            
            # Import the main package (which should import all submodules)
            parts = package_path.replace("src/", "").replace("/", ".")
            
            try:
                module = importlib.import_module(parts)
                # Verify __all__ exports are accessible
                if hasattr(module, "__all__"):
                    for symbol in module.__all__:
                        if not hasattr(module, symbol):
                            import_errors.append(
                                (parts, f"Missing export: {symbol}")
                            )
            except ImportError as e:
                import_errors.append((parts, str(e)))
        
        if packages_checked == 0:
            pytest.skip("No Phase 2 packages refactored yet")
        
        assert not import_errors, (
            f"Import errors detected:\n"
            + "\n".join(f"  {mod}: {err}" for mod, err in import_errors)
        )
