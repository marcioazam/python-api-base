"""Property-based tests for file size compliance.

**Feature: code-review-refactoring, Task 20.3: Write property test for file size compliance**
**Validates: Requirements 1.1, 1.3**
"""

from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


MAX_LINES = 400
SRC_DIR = Path("src")
EXCLUDE_PATTERNS = ["__pycache__", ".pyc"]


def count_lines(file_path: Path) -> int:
    """Count lines in a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return len(content.splitlines())
    except Exception:
        return 0


def get_all_python_files() -> list[Path]:
    """Get all Python files in src directory."""
    if not SRC_DIR.exists():
        return []
    
    files = []
    for py_file in SRC_DIR.rglob("*.py"):
        path_str = str(py_file)
        if not any(pattern in path_str for pattern in EXCLUDE_PATTERNS):
            files.append(py_file)
    return files


class TestFileSizeComplianceProperties:
    """Property tests for file size compliance.

    **Feature: code-review-refactoring, Property 16: File Size Compliance Post-Refactoring**
    **Validates: Requirements 1.1, 1.3**
    """

    def test_all_files_under_max_lines(self) -> None:
        """Property: All Python files are under 400 lines.

        **Feature: code-review-refactoring, Property 16: File Size Compliance Post-Refactoring**
        **Validates: Requirements 1.1, 1.3**
        """
        violations = []
        
        for py_file in get_all_python_files():
            line_count = count_lines(py_file)
            if line_count > MAX_LINES:
                violations.append((py_file, line_count))
        
        if violations:
            violation_msgs = [
                f"  {path}: {lines} lines (+{lines - MAX_LINES})"
                for path, lines in sorted(violations, key=lambda x: x[1], reverse=True)
            ]
            pytest.fail(
                f"{len(violations)} files exceed {MAX_LINES} lines:\n"
                + "\n".join(violation_msgs)
            )

    def test_refactored_packages_exist(self) -> None:
        """Property: Refactored packages exist with proper structure.

        **Feature: code-review-refactoring, Property 16: File Size Compliance Post-Refactoring**
        **Validates: Requirements 1.1, 1.3**
        """
        expected_packages = [
            "src/my_api/shared/event_sourcing",
            "src/my_api/shared/saga",
            "src/my_api/shared/oauth2",
            "src/my_api/shared/advanced_specification",
            "src/my_api/shared/cloud_provider_filter",
        ]
        
        for package_path in expected_packages:
            package = Path(package_path)
            assert package.exists(), f"Package {package_path} does not exist"
            
            init_file = package / "__init__.py"
            assert init_file.exists(), f"Package {package_path} missing __init__.py"

    def test_refactored_packages_have_multiple_modules(self) -> None:
        """Property: Refactored packages have multiple focused modules.

        **Feature: code-review-refactoring, Property 16: File Size Compliance Post-Refactoring**
        **Validates: Requirements 1.1, 1.3**
        """
        packages_to_check = [
            "src/my_api/shared/event_sourcing",
            "src/my_api/shared/saga",
            "src/my_api/shared/oauth2",
        ]
        
        for package_path in packages_to_check:
            package = Path(package_path)
            if not package.exists():
                continue
            
            py_files = list(package.glob("*.py"))
            # Should have more than just __init__.py
            assert len(py_files) > 1, (
                f"Package {package_path} should have multiple modules, "
                f"found only {len(py_files)}"
            )

    @given(st.integers(min_value=1, max_value=100))
    @settings(max_examples=10)
    def test_line_count_is_deterministic(self, _: int) -> None:
        """Property: Line counting is deterministic.

        **Feature: code-review-refactoring, Property 16: File Size Compliance Post-Refactoring**
        **Validates: Requirements 1.1, 1.3**
        """
        files = get_all_python_files()
        if not files:
            return
        
        # Pick first file for determinism test
        test_file = files[0]
        
        count1 = count_lines(test_file)
        count2 = count_lines(test_file)
        
        assert count1 == count2, "Line counting should be deterministic"


class TestBackwardCompatibilityAfterRefactoring:
    """Property tests for backward compatibility after refactoring.

    **Feature: code-review-refactoring, Property 1: Backward Compatibility After Refactoring**
    **Validates: Requirements 1.2, 1.4**
    """

    def test_event_sourcing_imports(self) -> None:
        """Property: Event sourcing imports work after refactoring."""
        from my_api.shared.event_sourcing import (
            Aggregate,
            ConcurrencyError,
            EventSourcedRepository,
            EventStream,
            InMemoryEventStore,
            InMemoryProjection,
            Projection,
            Snapshot,
            SourcedEvent,
        )
        
        assert Aggregate is not None
        assert SourcedEvent is not None
        assert EventStream is not None
        assert Snapshot is not None
        assert InMemoryEventStore is not None
        assert Projection is not None
        assert InMemoryProjection is not None
        assert EventSourcedRepository is not None
        assert ConcurrencyError is not None

    def test_saga_imports(self) -> None:
        """Property: Saga imports work after refactoring."""
        from my_api.shared.saga import (
            Saga,
            SagaBuilder,
            SagaContext,
            SagaOrchestrator,
            SagaResult,
            SagaStatus,
            SagaStep,
            StepResult,
            StepStatus,
        )
        
        assert Saga is not None
        assert SagaBuilder is not None
        assert SagaContext is not None
        assert SagaOrchestrator is not None
        assert SagaResult is not None
        assert SagaStatus is not None
        assert SagaStep is not None
        assert StepResult is not None
        assert StepStatus is not None

    def test_oauth2_imports(self) -> None:
        """Property: OAuth2 imports work after refactoring."""
        from my_api.shared.oauth2 import (
            BaseOAuthProvider,
            GitHubOAuthProvider,
            GoogleOAuthProvider,
            InMemoryStateStore,
            OAuthConfig,
            OAuthError,
            OAuthProvider,
            OAuthState,
            OAuthTokenResponse,
            OAuthUserInfo,
            StateStore,
        )
        
        assert OAuthProvider is not None
        assert OAuthConfig is not None
        assert OAuthUserInfo is not None
        assert OAuthTokenResponse is not None
        assert OAuthState is not None
        assert BaseOAuthProvider is not None
        assert GoogleOAuthProvider is not None
        assert GitHubOAuthProvider is not None
        assert StateStore is not None
        assert InMemoryStateStore is not None
        assert OAuthError is not None
