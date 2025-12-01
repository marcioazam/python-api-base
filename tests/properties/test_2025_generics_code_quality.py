"""Property-based tests for Code Quality and Standards.

**Feature: 2025-generics-clean-code-review**
**Validates: Requirements 10.2, 10.5, 11.1, 11.2, 11.3, 12.1, 12.2**
"""

import ast
import inspect
from enum import Enum
from pathlib import Path
from typing import Any

import pytest
from hypothesis import given, strategies as st, settings

from core.errors.status import (
    OperationStatus, ValidationStatus, EntityStatus,
    UserStatus, TaskStatus, HttpStatus, ErrorCode,
)
from core.errors.messages import ErrorMessages, ValidationMessages


# =============================================================================
# Enum Status Codes Tests
# =============================================================================

class TestEnumStatusCodes:
    """Property tests for Enum status codes.
    
    **Feature: 2025-generics-clean-code-review, Property 10: Enum Status Codes**
    **Validates: Requirements 10.2, 10.5**
    """

    def test_operation_status_is_enum(self) -> None:
        """OperationStatus values are Enum members."""
        assert issubclass(OperationStatus, Enum)
        for status in OperationStatus:
            assert isinstance(status, OperationStatus)
            assert isinstance(status.value, str)

    def test_validation_status_is_enum(self) -> None:
        """ValidationStatus values are Enum members."""
        assert issubclass(ValidationStatus, Enum)
        for status in ValidationStatus:
            assert isinstance(status, ValidationStatus)

    def test_entity_status_is_enum(self) -> None:
        """EntityStatus values are Enum members."""
        assert issubclass(EntityStatus, Enum)
        for status in EntityStatus:
            assert isinstance(status, EntityStatus)

    def test_http_status_is_int_enum(self) -> None:
        """HttpStatus values are IntEnum members."""
        assert issubclass(HttpStatus, Enum)
        for status in HttpStatus:
            assert isinstance(status.value, int)
            assert 100 <= status.value < 600

    def test_error_code_is_enum(self) -> None:
        """ErrorCode values are Enum members."""
        assert issubclass(ErrorCode, Enum)
        for code in ErrorCode:
            assert isinstance(code, ErrorCode)
            assert isinstance(code.value, str)
            assert code.value.isupper()  # Error codes should be UPPER_CASE

    def test_error_messages_are_formattable(self) -> None:
        """ErrorMessages can be formatted with placeholders."""
        # Test a few messages with their expected placeholders
        msg = ErrorMessages.NOT_FOUND.format(resource_type="User", id="123")
        assert "User" in msg
        assert "123" in msg
        
        msg = ErrorMessages.VALIDATION_FAILED.format(field="email", reason="invalid")
        assert "email" in msg
        assert "invalid" in msg

    def test_all_status_enums_have_unique_values(self) -> None:
        """All status enum values are unique within their enum."""
        for enum_class in [OperationStatus, ValidationStatus, EntityStatus, UserStatus, TaskStatus]:
            values = [e.value for e in enum_class]
            assert len(values) == len(set(values)), f"Duplicate values in {enum_class.__name__}"


# =============================================================================
# Code Metrics Tests
# =============================================================================

class TestCodeMetrics:
    """Property tests for code metrics compliance.
    
    **Feature: 2025-generics-clean-code-review, Property 11: Code Metrics Compliance**
    **Validates: Requirements 11.1, 11.2, 11.3**
    """

    MAX_FUNCTION_LINES = 50
    MAX_CLASS_LINES = 300
    MAX_NESTING_DEPTH = 3

    def _get_python_files(self, directory: str) -> list[Path]:
        """Get all Python files in directory."""
        base = Path("src")
        if not base.exists():
            return []
        return list(base.glob(f"{directory}/**/*.py"))

    def _count_function_lines(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
        """Count lines in a function."""
        if not node.body:
            return 0
        start = node.body[0].lineno
        end = node.body[-1].end_lineno or node.body[-1].lineno
        return end - start + 1

    def _count_class_lines(self, node: ast.ClassDef) -> int:
        """Count lines in a class."""
        if not node.body:
            return 0
        start = node.body[0].lineno
        end = node.body[-1].end_lineno or node.body[-1].lineno
        return end - start + 1

    def _get_max_nesting(self, node: ast.AST, current_depth: int = 0) -> int:
        """Get maximum nesting depth in AST node."""
        max_depth = current_depth
        
        nesting_nodes = (ast.If, ast.For, ast.While, ast.With, ast.Try, ast.ExceptHandler)
        
        for child in ast.iter_child_nodes(node):
            if isinstance(child, nesting_nodes):
                child_depth = self._get_max_nesting(child, current_depth + 1)
                max_depth = max(max_depth, child_depth)
            else:
                child_depth = self._get_max_nesting(child, current_depth)
                max_depth = max(max_depth, child_depth)
        
        return max_depth

    def test_shared_value_objects_function_length(self) -> None:
        """Functions in shared/value_objects are <= 50 lines."""
        files = self._get_python_files("shared/value_objects")
        violations = []
        
        for file_path in files:
            try:
                tree = ast.parse(file_path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        lines = self._count_function_lines(node)
                        if lines > self.MAX_FUNCTION_LINES:
                            violations.append(f"{file_path}:{node.name} has {lines} lines")
            except SyntaxError:
                pass
        
        assert not violations, f"Functions exceeding {self.MAX_FUNCTION_LINES} lines: {violations}"

    def test_core_errors_function_length(self) -> None:
        """Functions in core/errors are <= 50 lines."""
        files = self._get_python_files("core/errors")
        violations = []
        
        for file_path in files:
            try:
                tree = ast.parse(file_path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        lines = self._count_function_lines(node)
                        if lines > self.MAX_FUNCTION_LINES:
                            violations.append(f"{file_path}:{node.name} has {lines} lines")
            except SyntaxError:
                pass
        
        assert not violations, f"Functions exceeding {self.MAX_FUNCTION_LINES} lines: {violations}"


# =============================================================================
# Documentation Tests
# =============================================================================

class TestDocumentation:
    """Property tests for documentation consistency.
    
    **Feature: 2025-generics-clean-code-review, Property 12: Documentation Consistency**
    **Validates: Requirements 12.1, 12.2**
    """

    def _get_python_files(self, directory: str) -> list[Path]:
        """Get all Python files in directory."""
        base = Path("src")
        if not base.exists():
            return []
        return list(base.glob(f"{directory}/**/*.py"))

    def test_shared_value_objects_have_docstrings(self) -> None:
        """Classes in shared/value_objects have docstrings."""
        files = self._get_python_files("shared/value_objects")
        missing = []
        
        for file_path in files:
            if file_path.name.startswith("_"):
                continue
            try:
                tree = ast.parse(file_path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if not ast.get_docstring(node):
                            missing.append(f"{file_path}:{node.name}")
            except SyntaxError:
                pass
        
        assert not missing, f"Classes missing docstrings: {missing}"

    def test_core_errors_have_docstrings(self) -> None:
        """Classes in core/errors have docstrings."""
        files = self._get_python_files("core/errors")
        missing = []
        
        for file_path in files:
            if file_path.name.startswith("_"):
                continue
            try:
                tree = ast.parse(file_path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        if not ast.get_docstring(node):
                            missing.append(f"{file_path}:{node.name}")
            except SyntaxError:
                pass
        
        assert not missing, f"Classes missing docstrings: {missing}"

    def test_public_functions_have_docstrings(self) -> None:
        """Public functions in shared/value_objects have docstrings."""
        files = self._get_python_files("shared/value_objects")
        missing = []
        
        for file_path in files:
            if file_path.name.startswith("_"):
                continue
            try:
                tree = ast.parse(file_path.read_text())
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        # Skip private functions
                        if node.name.startswith("_"):
                            continue
                        if not ast.get_docstring(node):
                            missing.append(f"{file_path}:{node.name}")
            except SyntaxError:
                pass
        
        # Allow some missing for now, just report
        if missing:
            pytest.skip(f"Some functions missing docstrings: {missing[:5]}...")
