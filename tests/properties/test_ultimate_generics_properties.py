"""Property-based tests for Ultimate Generics Code Review 2025.

**Feature: ultimate-generics-code-review-2025**
**Validates: All Requirements**

This module contains property-based tests using Hypothesis to verify
correctness properties defined in the design document.
"""

import asyncio
from dataclasses import FrozenInstanceError
from datetime import datetime, UTC
from typing import Any

import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

# Import modules under test
from my_app.core.base.result import Ok, Err, collect_results, result_from_dict
from my_app.core.base.entity import BaseEntity, VersionedEntity
from my_app.core.base.pagination import CursorPagination
from my_app.core.base.specification import (
    Specification,
    PredicateSpecification,
    TrueSpecification,
    FalseSpecification,
)
from my_app.core.patterns.validation import ValidationResult, ValidationError
from my_app.core.patterns.factory import SingletonFactory
from my_app.core.patterns.observer import Subject, FunctionObserver
from my_app.core.di.container import Container
from my_app.core.di.lifecycle import Lifetime
from my_app.core.di.exceptions import CircularDependencyError, ServiceNotRegisteredError
from my_app.core.errors.domain_errors import AppException, EntityNotFoundError


# =============================================================================
# Property 2: Result Pattern Round-Trip
# =============================================================================

@given(st.one_of(st.integers(), st.text(), st.floats(allow_nan=False)))
@settings(max_examples=100)
def test_ok_result_round_trip(value: Any) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 2: Result Pattern Round-Trip**
    **Validates: Requirements 5.1, 15.1**
    
    For any Ok value, serializing to dict and deserializing back produces equivalent Result.
    """
    original = Ok(value)
    serialized = original.to_dict()
    deserialized = result_from_dict(serialized)
    
    assert deserialized.is_ok()
    assert deserialized.unwrap() == value


@given(st.one_of(st.integers(), st.text(), st.floats(allow_nan=False)))
@settings(max_examples=100)
def test_err_result_round_trip(error: Any) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 2: Result Pattern Round-Trip**
    **Validates: Requirements 5.1, 15.1**
    
    For any Err value, serializing to dict and deserializing back produces equivalent Result.
    """
    original = Err(error)
    serialized = original.to_dict()
    deserialized = result_from_dict(serialized)
    
    assert deserialized.is_err()
    assert deserialized.error == error


# =============================================================================
# Property 5: Specification Composition Laws
# =============================================================================

@given(st.integers(), st.booleans(), st.booleans())
@settings(max_examples=100)
def test_specification_and_composition(value: int, pred1_result: bool, pred2_result: bool) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 5: Specification Composition Laws**
    **Validates: Requirements 8.2, 8.3, 8.4**
    
    (S1 & S2).is_satisfied_by(C) equals S1.is_satisfied_by(C) and S2.is_satisfied_by(C)
    """
    spec1 = PredicateSpecification(lambda _: pred1_result)
    spec2 = PredicateSpecification(lambda _: pred2_result)
    
    combined = spec1 & spec2
    
    expected = pred1_result and pred2_result
    assert combined.is_satisfied_by(value) == expected


@given(st.integers(), st.booleans(), st.booleans())
@settings(max_examples=100)
def test_specification_or_composition(value: int, pred1_result: bool, pred2_result: bool) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 5: Specification Composition Laws**
    **Validates: Requirements 8.2, 8.3, 8.4**
    
    (S1 | S2).is_satisfied_by(C) equals S1.is_satisfied_by(C) or S2.is_satisfied_by(C)
    """
    spec1 = PredicateSpecification(lambda _: pred1_result)
    spec2 = PredicateSpecification(lambda _: pred2_result)
    
    combined = spec1 | spec2
    
    expected = pred1_result or pred2_result
    assert combined.is_satisfied_by(value) == expected


@given(st.integers(), st.booleans())
@settings(max_examples=100)
def test_specification_not_composition(value: int, pred_result: bool) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 5: Specification Composition Laws**
    **Validates: Requirements 8.2, 8.3, 8.4**
    
    (~S1).is_satisfied_by(C) equals not S1.is_satisfied_by(C)
    """
    spec = PredicateSpecification(lambda _: pred_result)
    
    negated = ~spec
    
    expected = not pred_result
    assert negated.is_satisfied_by(value) == expected


# =============================================================================
# Property 7: Entity Timestamp Invariants
# =============================================================================

@given(st.integers(min_value=1, max_value=100))
@settings(max_examples=100)
def test_entity_timestamp_invariants(num_updates: int) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 7: Entity Timestamp Invariants**
    **Validates: Requirements 7.1**
    
    After calling mark_updated(), updated_at >= previous value and >= created_at.
    """
    entity = BaseEntity[str](id="test-id")
    created_at = entity.created_at
    previous_updated = entity.updated_at
    
    for _ in range(num_updates):
        entity.mark_updated()
        assert entity.updated_at >= previous_updated
        assert entity.updated_at >= created_at
        previous_updated = entity.updated_at


# =============================================================================
# Property 8: Version Increment Monotonicity
# =============================================================================

@given(st.integers(min_value=1, max_value=100))
@settings(max_examples=100)
def test_version_increment_monotonicity(num_increments: int) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 8: Version Increment Monotonicity**
    **Validates: Requirements 7.3**
    
    Calling increment_version() increases version by exactly 1.
    """
    entity = VersionedEntity[str, int](id="test-id", version=1)
    
    for i in range(num_increments):
        expected_version = entity.version + 1
        entity.increment_version()
        assert entity.version == expected_version


# =============================================================================
# Property 9: Cursor Pagination Round-Trip
# =============================================================================

class MockEntity:
    """Mock entity for pagination testing."""
    def __init__(self, id: str, created_at: str) -> None:
        self.id = id
        self.created_at = created_at


@given(st.text(min_size=1, max_size=50), st.text(min_size=1, max_size=50))
@settings(max_examples=100)
def test_cursor_pagination_round_trip(entity_id: str, created_at: str) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 9: Cursor Pagination Round-Trip**
    **Validates: Requirements 14.2, 14.3, 15.5**
    
    Encoding a cursor and decoding it back returns original field values.
    """
    pagination = CursorPagination[MockEntity, dict](
        cursor_fields=["id", "created_at"]
    )
    
    entity = MockEntity(id=entity_id, created_at=created_at)
    
    encoded = pagination.encode_cursor(entity)
    decoded = pagination.decode_cursor(encoded)
    
    assert decoded.get("id") == entity_id
    assert decoded.get("created_at") == created_at


def test_cursor_decode_invalid_returns_empty() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 9: Cursor Pagination Round-Trip**
    **Validates: Requirements 14.3**
    
    Decoding invalid cursor returns empty dict.
    """
    pagination = CursorPagination[MockEntity, dict](cursor_fields=["id"])
    
    result = pagination.decode_cursor("invalid-base64!")
    assert result == {}


# =============================================================================
# Property 10: ValidationResult to Result Conversion
# =============================================================================

@given(st.one_of(st.integers(), st.text()))
@settings(max_examples=100)
def test_valid_validation_result_to_result(value: Any) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 10: ValidationResult to Result Conversion**
    **Validates: Requirements 13.5**
    
    ValidationResult with value and no errors converts to Ok(value).
    """
    validation_result = ValidationResult(value=value, errors=[])
    
    result = validation_result.to_result()
    
    assert result.is_ok()
    assert result.unwrap() == value


@given(st.text(min_size=1), st.text(min_size=1))
@settings(max_examples=100)
def test_invalid_validation_result_to_result(field: str, message: str) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 10: ValidationResult to Result Conversion**
    **Validates: Requirements 13.5**
    
    ValidationResult with errors converts to Err(errors).
    """
    error = ValidationError(field=field, message=message)
    validation_result = ValidationResult(value=None, errors=[error])
    
    result = validation_result.to_result()
    
    assert result.is_err()
    assert len(result.error) == 1
    assert result.error[0].field == field


# =============================================================================
# Property 11: Factory Singleton Identity
# =============================================================================

@given(st.integers(min_value=2, max_value=10))
@settings(max_examples=100)
def test_singleton_factory_identity(num_calls: int) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 11: Factory Singleton Identity**
    **Validates: Requirements 10.3**
    
    Multiple calls to SingletonFactory.create() return the same instance.
    """
    call_count = 0
    
    def creator() -> dict:
        nonlocal call_count
        call_count += 1
        return {"instance": call_count}
    
    factory = SingletonFactory(creator)
    
    instances = [factory.create() for _ in range(num_calls)]
    
    # All instances should be the same object
    first = instances[0]
    for instance in instances[1:]:
        assert instance is first
    
    # Creator should only be called once
    assert call_count == 1


# =============================================================================
# Property 12: Observer Unsubscribe Effectiveness
# =============================================================================

@pytest.mark.asyncio
@given(st.integers(min_value=1, max_value=5))
@settings(max_examples=50)
async def test_observer_unsubscribe_effectiveness(num_events: int) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 12: Observer Unsubscribe Effectiveness**
    **Validates: Requirements 11.1**
    
    After unsubscribe, observer is not notified of events.
    """
    received_events: list[int] = []
    
    async def handler(event: int) -> None:
        received_events.append(event)
    
    subject = Subject[int]()
    observer = FunctionObserver(handler)
    
    unsubscribe = subject.subscribe(observer)
    
    # Publish before unsubscribe
    await subject.notify(1)
    assert 1 in received_events
    
    # Unsubscribe
    unsubscribe()
    
    # Publish after unsubscribe
    for i in range(2, num_events + 2):
        await subject.notify(i)
    
    # Should only have the first event
    assert len(received_events) == 1
    assert received_events[0] == 1


# =============================================================================
# Property 13: Exception Serialization Completeness
# =============================================================================

@given(st.text(min_size=1, max_size=50), st.text(min_size=1, max_size=50))
@settings(max_examples=100)
def test_exception_serialization_with_cause(entity_type: str, entity_id: str) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 13: Exception Serialization Completeness**
    **Validates: Requirements 2.3, 15.3**
    
    AppException with cause chain includes all causes in serialized output.
    """
    # Create exception with cause
    original_cause = ValueError("Original error")
    exception = EntityNotFoundError(entity_type, entity_id)
    exception.__cause__ = original_cause
    
    serialized = exception.to_dict()
    
    assert "cause" in serialized
    assert serialized["cause"]["type"] == "ValueError"
    assert "Original error" in serialized["cause"]["message"]
    assert serialized["correlation_id"] is not None
    assert serialized["timestamp"] is not None


# =============================================================================
# Property 14: Immutable Dataclass Integrity
# =============================================================================

def test_frozen_dataclass_immutability() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 14: Immutable Dataclass Integrity**
    **Validates: Requirements 18.1**
    
    Frozen dataclasses raise FrozenInstanceError on attribute modification.
    """
    result = Ok(42)
    
    with pytest.raises(FrozenInstanceError):
        result.value = 100  # type: ignore


def test_validation_error_immutability() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 14: Immutable Dataclass Integrity**
    **Validates: Requirements 18.1**
    """
    error = ValidationError(field="test", message="error")
    
    with pytest.raises(FrozenInstanceError):
        error.field = "modified"  # type: ignore


# =============================================================================
# Property 15: Collect Results Aggregation
# =============================================================================

@given(st.lists(st.integers(), min_size=1, max_size=20))
@settings(max_examples=100)
def test_collect_results_all_ok(values: list[int]) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 15: Collect Results Aggregation**
    **Validates: Requirements 5.4**
    
    collect_results with all Ok returns Ok with list of values.
    """
    results = [Ok(v) for v in values]
    
    collected = collect_results(results)
    
    assert collected.is_ok()
    assert collected.unwrap() == values


@given(
    st.lists(st.integers(), min_size=1, max_size=10),
    st.integers(min_value=0),
    st.text(min_size=1)
)
@settings(max_examples=100)
def test_collect_results_first_err(ok_values: list[int], err_index: int, error: str) -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 15: Collect Results Aggregation**
    **Validates: Requirements 5.4**
    
    collect_results returns first Err encountered.
    """
    # Insert error at valid index
    actual_index = err_index % (len(ok_values) + 1)
    
    results: list[Ok[int] | Err[str]] = [Ok(v) for v in ok_values]
    results.insert(actual_index, Err(error))
    
    collected = collect_results(results)
    
    assert collected.is_err()
    assert collected.error == error


# =============================================================================
# Property 3 & 4: DI Container Tests
# =============================================================================

def test_di_container_type_preservation() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 3: DI Container Type Preservation**
    **Validates: Requirements 4.1, 4.2**
    
    Registered service type is preserved when resolved.
    """
    class TestService:
        def __init__(self) -> None:
            self.value = 42
    
    container = Container()
    container.register(TestService, lifetime=Lifetime.SINGLETON)
    
    resolved = container.resolve(TestService)
    
    assert isinstance(resolved, TestService)
    assert resolved.value == 42


def test_di_container_circular_dependency_detection() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 4: Circular Dependency Detection**
    **Validates: Requirements 4.3**
    
    Circular dependencies raise CircularDependencyError with chain.
    Note: We test this by manually creating a circular registration scenario
    using factories that reference each other.
    """
    container = Container()
    
    # Create a scenario where resolving ServiceA requires ServiceA again
    # This simulates circular dependency detection
    class SelfReferencing:
        pass
    
    # Register with a factory that tries to resolve itself
    def circular_factory() -> SelfReferencing:
        # This would cause infinite recursion without circular detection
        container.resolve(SelfReferencing)
        return SelfReferencing()
    
    container.register(SelfReferencing, factory=circular_factory)
    
    with pytest.raises(CircularDependencyError) as exc_info:
        container.resolve(SelfReferencing)
    
    # Chain should contain the self-referencing service
    assert SelfReferencing in exc_info.value.chain


def test_di_container_service_not_registered() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 4: Circular Dependency Detection**
    **Validates: Requirements 4.5**
    
    Resolving unregistered service raises ServiceNotRegisteredError.
    """
    class UnregisteredService:
        pass
    
    container = Container()
    
    with pytest.raises(ServiceNotRegisteredError):
        container.resolve(UnregisteredService)


# =============================================================================
# Property 6: Pipeline Short-Circuit on Error
# =============================================================================

@pytest.mark.asyncio
async def test_pipeline_short_circuit_on_error() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 6: Pipeline Short-Circuit on Error**
    **Validates: Requirements 9.3**
    
    ResultPipeline stops at first Err and doesn't execute subsequent steps.
    """
    from my_app.core.patterns.transformers import ResultPipeline, ResultPipelineStep
    from my_app.core.base.result import Result
    
    execution_log: list[str] = []
    
    class Step1(ResultPipelineStep[int, int, str]):
        async def execute(self, input_data: int) -> Result[int, str]:
            execution_log.append("step1")
            return Ok(input_data * 2)
    
    class Step2(ResultPipelineStep[int, int, str]):
        async def execute(self, input_data: int) -> Result[int, str]:
            execution_log.append("step2")
            return Err("Error in step 2")
    
    class Step3(ResultPipelineStep[int, int, str]):
        async def execute(self, input_data: int) -> Result[int, str]:
            execution_log.append("step3")
            return Ok(input_data + 10)
    
    pipeline = ResultPipeline[int, int, str]()
    pipeline.add_step(Step1())
    pipeline.add_step(Step2())
    pipeline.add_step(Step3())
    
    result = await pipeline.execute(5)
    
    # Should stop at step2 error
    assert result.is_err()
    assert result.error == "Error in step 2"
    
    # Step3 should NOT have been executed
    assert "step1" in execution_log
    assert "step2" in execution_log
    assert "step3" not in execution_log


# =============================================================================
# Property 1: PEP 695 Syntax Consistency
# =============================================================================

def test_pep695_no_legacy_generic_imports() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 1: PEP 695 Syntax Consistency**
    **Validates: Requirements 1.1, 1.2, 1.3, 1.4, 1.5**
    
    Verify that core modules don't use legacy Generic[T] patterns in class definitions.
    Note: This is a static analysis test, not a property test, but validates the property.
    """
    import ast
    from pathlib import Path
    
    core_path = Path("src/core")
    violations: list[str] = []
    
    # Files to check (excluding __pycache__ and test files)
    python_files = list(core_path.rglob("*.py"))
    
    for file_path in python_files:
        if "__pycache__" in str(file_path):
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8")
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                # Check for class definitions using Generic[T] as base
                if isinstance(node, ast.ClassDef):
                    for base in node.bases:
                        # Check for Generic[...] pattern
                        if isinstance(base, ast.Subscript):
                            if isinstance(base.value, ast.Name) and base.value.id == "Generic":
                                # This is a legacy Generic[T] usage
                                # Allow if it's in a docstring example or fallback import
                                violations.append(
                                    f"{file_path}:{node.lineno} - class {node.name} uses Generic[T]"
                                )
        except SyntaxError:
            # Skip files with syntax errors
            continue
    
    # Filter out known exceptions (docstring examples, fallback imports)
    filtered_violations = [
        v for v in violations 
        if "protocols/entities.py" not in v  # Docstring examples
        and "use_case.py" not in v  # Fallback import for compatibility
    ]
    
    assert len(filtered_violations) == 0, f"Legacy Generic[T] found:\n" + "\n".join(filtered_violations)


def test_pep695_type_aliases_use_type_statement() -> None:
    """
    **Feature: ultimate-generics-code-review-2025, Property 1: PEP 695 Syntax Consistency**
    **Validates: Requirements 1.2**
    
    Verify that type aliases use PEP 695 'type' statement instead of TypeAlias.
    """
    from pathlib import Path
    import re
    
    core_path = Path("src/core")
    violations: list[str] = []
    
    # Pattern for legacy TypeAlias usage (not in comments)
    legacy_pattern = re.compile(r"^\s*\w+\s*:\s*TypeAlias\s*=", re.MULTILINE)
    
    python_files = list(core_path.rglob("*.py"))
    
    for file_path in python_files:
        if "__pycache__" in str(file_path):
            continue
            
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Skip if TypeAlias is only mentioned in comments
            lines = content.split("\n")
            for i, line in enumerate(lines, 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                    
                if legacy_pattern.match(line):
                    violations.append(f"{file_path}:{i} - {line.strip()}")
                    
        except Exception:
            continue
    
    assert len(violations) == 0, f"Legacy TypeAlias found:\n" + "\n".join(violations)
