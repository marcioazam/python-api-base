"""Property-based tests for deep code quality and generics review.

**Feature: deep-code-quality-generics-review**
**Validates: Requirements 1.1, 8.1, 12.1, 14.2, 14.3, 14.6**
"""

import ast
import sys
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st


class TestPEP695SyntaxCompliance:
    """Property tests for PEP 695 syntax compliance.
    
    **Feature: deep-code-quality-generics-review, Property 1: PEP 695 Syntax Compliance**
    **Validates: Requirements 1.1**
    """

    def test_sqlmodel_repository_uses_pep695_syntax(self) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 1: PEP 695 Syntax Compliance**
        **Validates: Requirements 1.1, 14.2**
        
        SQLModelRepository SHALL use PEP 695 type parameter syntax.
        """
        file_path = Path("src/my_app/adapters/repositories/sqlmodel_repository.py")
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        
        # Check that old TypeVar syntax is NOT present
        assert "TypeVar" not in source, "Old TypeVar syntax should not be present"
        assert "Generic[" not in source, "Old Generic[] syntax should not be present"
        
        # Check that class uses PEP 695 syntax (class Name[T: Bound])
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "SQLModelRepository":
                # In Python 3.12+, type_params attribute exists for PEP 695
                assert hasattr(node, "type_params"), "Class should have type_params"
                assert len(node.type_params) == 3, "Should have 3 type parameters"
                break
        else:
            pytest.fail("SQLModelRepository class not found")

    def test_circuit_breaker_uses_pep695_syntax(self) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 1: PEP 695 Syntax Compliance**
        **Validates: Requirements 1.1**
        
        CircuitBreaker SHALL use PEP 695 type parameter syntax.
        """
        file_path = Path("src/my_app/shared/circuit_breaker.py")
        source = file_path.read_text(encoding="utf-8")
        
        # Check that old ParamSpec/TypeVar syntax is NOT present
        assert "ParamSpec" not in source, "Old ParamSpec syntax should not be present"
        assert 'T = TypeVar("T")' not in source, "Old TypeVar syntax should not be present"
        assert 'P = ParamSpec("P")' not in source, "Old ParamSpec syntax should not be present"

    def test_aggregate_uses_pep695_syntax(self) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 1: PEP 695 Syntax Compliance**
        **Validates: Requirements 1.1**
        
        Aggregate SHALL use PEP 695 type parameter syntax.
        """
        file_path = Path("src/my_app/shared/event_sourcing/aggregate.py")
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
        
        # Check that old TypeVar/Generic syntax is NOT present
        assert 'AggregateId = TypeVar("AggregateId"' not in source, (
            "Old TypeVar syntax should not be present"
        )
        assert "Generic[AggregateId]" not in source, (
            "Old Generic[] syntax should not be present"
        )
        
        # Check that class uses PEP 695 syntax
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "Aggregate":
                assert hasattr(node, "type_params"), "Class should have type_params"
                assert len(node.type_params) == 1, "Should have 1 type parameter"
                break
        else:
            pytest.fail("Aggregate class not found")


class TestDataclassMemoryOptimization:
    """Property tests for dataclass memory optimization.
    
    **Feature: deep-code-quality-generics-review, Property 2: Dataclass Memory Optimization**
    **Validates: Requirements 8.1, 12.1**
    """

    def test_error_context_has_slots(self) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 2: Dataclass Memory Optimization**
        **Validates: Requirements 8.1, 12.1, 14.6**
        
        ErrorContext SHALL use slots=True for memory optimization.
        """
        from core.exceptions import ErrorContext
        
        # Check that __slots__ is defined (slots=True in dataclass)
        assert hasattr(ErrorContext, "__slots__"), (
            "ErrorContext should have __slots__ defined"
        )
        
        # Verify it's a frozen dataclass
        from dataclasses import fields
        
        # Check that the class is frozen (immutable)
        context = ErrorContext()
        with pytest.raises(AttributeError):
            context.correlation_id = "new_value"  # type: ignore

    def test_error_context_memory_efficiency(self) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 2: Dataclass Memory Optimization**
        **Validates: Requirements 12.1**
        
        ErrorContext with slots SHALL use less memory than without slots.
        """
        from core.exceptions import ErrorContext
        
        # Create instance and verify no __dict__ (slots optimization)
        context = ErrorContext()
        assert not hasattr(context, "__dict__"), (
            "ErrorContext should not have __dict__ when using slots"
        )


class TestCallableTypeHint:
    """Property tests for proper Callable type hints.
    
    **Feature: deep-code-quality-generics-review**
    **Validates: Requirements 14.3**
    """

    def test_inmemory_repository_uses_callable_type(self) -> None:
        """
        **Feature: deep-code-quality-generics-review**
        **Validates: Requirements 14.3**
        
        InMemoryRepository SHALL use Callable type hint instead of callable.
        """
        file_path = Path("src/my_app/shared/repository.py")
        source = file_path.read_text(encoding="utf-8")
        
        # Check that lowercase 'callable' is NOT used as type hint
        assert "id_generator: callable" not in source, (
            "Should use Callable[[], str] instead of callable"
        )
        
        # Check that proper Callable type is used
        assert "Callable[[], str]" in source, (
            "Should use Callable[[], str] type hint"
        )
        
        # Check that Callable is imported from collections.abc
        assert "from collections.abc import Callable" in source, (
            "Callable should be imported from collections.abc"
        )


class TestResultPatternCompliance:
    """Property tests for Result pattern compliance.
    
    **Feature: deep-code-quality-generics-review, Property 3: Result Pattern Completeness**
    **Validates: Requirements 4.2, 4.3, 4.4**
    """

    @settings(max_examples=100)
    @given(value=st.integers())
    def test_ok_map_preserves_value(self, value: int) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 3: Result Pattern Completeness**
        **Validates: Requirements 4.3**
        
        For any Ok value, map SHALL apply the function to the value.
        """
        from core.shared.result import Ok
        
        ok = Ok(value)
        mapped = ok.map(lambda x: x * 2)
        
        assert mapped.value == value * 2

    @settings(max_examples=100)
    @given(error=st.text(min_size=1, max_size=50))
    def test_err_map_err_preserves_error(self, error: str) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 3: Result Pattern Completeness**
        **Validates: Requirements 4.3**
        
        For any Err value, map_err SHALL apply the function to the error.
        """
        from core.shared.result import Err
        
        err = Err(error)
        mapped = err.map_err(lambda e: f"Error: {e}")
        
        assert mapped.error == f"Error: {error}"

    @settings(max_examples=100)
    @given(value=st.integers(), default=st.integers())
    def test_ok_unwrap_or_returns_value(self, value: int, default: int) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 3: Result Pattern Completeness**
        **Validates: Requirements 4.4**
        
        For any Ok value, unwrap_or SHALL return the value, not the default.
        """
        from core.shared.result import Ok
        
        ok = Ok(value)
        result = ok.unwrap_or(default)
        
        assert result == value

    @settings(max_examples=100)
    @given(error=st.text(min_size=1), default=st.integers())
    def test_err_unwrap_or_returns_default(self, error: str, default: int) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 3: Result Pattern Completeness**
        **Validates: Requirements 4.4**
        
        For any Err value, unwrap_or SHALL return the default.
        """
        from core.shared.result import Err
        
        err = Err(error)
        result = err.unwrap_or(default)
        
        assert result == default


class TestExceptionSerializationConsistency:
    """Property tests for exception serialization consistency.
    
    **Feature: deep-code-quality-generics-review, Property 10: Exception Serialization Consistency**
    **Validates: Requirements 8.2, 8.5**
    """

    @settings(max_examples=50)
    @given(
        message=st.text(min_size=1, max_size=100),
        error_code=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_")),
        status_code=st.integers(min_value=400, max_value=599),
    )
    def test_app_exception_to_dict_has_consistent_keys(
        self, message: str, error_code: str, status_code: int
    ) -> None:
        """
        **Feature: deep-code-quality-generics-review, Property 10: Exception Serialization Consistency**
        **Validates: Requirements 8.2, 8.5**
        
        For any AppException, to_dict() SHALL return consistent keys.
        """
        from core.exceptions import AppException
        
        exc = AppException(
            message=message,
            error_code=error_code,
            status_code=status_code,
        )
        
        result = exc.to_dict()
        
        # Check all required keys are present
        required_keys = {"message", "error_code", "status_code", "details", "correlation_id", "timestamp"}
        assert required_keys.issubset(result.keys()), (
            f"Missing keys: {required_keys - set(result.keys())}"
        )
        
        # Check values match
        assert result["message"] == message
        assert result["error_code"] == error_code
        assert result["status_code"] == status_code

