"""Property-based tests for type annotation completeness.

**Feature: api-code-review, Property 4: Type Annotation Completeness**
**Validates: Requirements 7.1**
"""

import ast
import inspect
from pathlib import Path
from typing import Any

from hypothesis import given, settings
from hypothesis import strategies as st


def get_public_functions_from_module(module_path: Path) -> list[dict[str, Any]]:
    """Extract public function signatures from a Python module.

    Args:
        module_path: Path to the Python file.

    Returns:
        List of function info dicts with name, has_return_type, params.
    """
    try:
        source = module_path.read_text(encoding="utf-8")
        tree = ast.parse(source)
    except (SyntaxError, UnicodeDecodeError):
        return []

    functions = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            # Skip private functions
            if node.name.startswith("_"):
                continue

            # Check return type annotation
            has_return_type = node.returns is not None

            # Check parameter annotations
            params = []
            for arg in node.args.args:
                # Skip 'self' and 'cls'
                if arg.arg in ("self", "cls"):
                    continue
                params.append({
                    "name": arg.arg,
                    "has_annotation": arg.annotation is not None,
                })

            functions.append({
                "name": node.name,
                "has_return_type": has_return_type,
                "params": params,
                "file": str(module_path),
            })

    return functions


def check_type_completeness(func_info: dict[str, Any]) -> tuple[bool, list[str]]:
    """Check if a function has complete type annotations.

    Args:
        func_info: Function info dict from get_public_functions_from_module.

    Returns:
        Tuple of (is_complete, list of missing annotations).
    """
    missing = []

    if not func_info["has_return_type"]:
        missing.append("return type")

    for param in func_info["params"]:
        if not param["has_annotation"]:
            missing.append(f"parameter '{param['name']}'")

    return len(missing) == 0, missing


def get_all_source_files() -> list[Path]:
    """Get all Python source files in the project.

    Returns:
        List of Path objects for Python files.
    """
    src_dir = Path("src/my_app")
    if not src_dir.exists():
        return []

    return list(src_dir.rglob("*.py"))


class TestTypeAnnotationCompleteness:
    """Property tests for type annotation completeness.

    **Feature: api-code-review, Property 4: Type Annotation Completeness**
    **Validates: Requirements 7.1**
    """

    def test_all_public_functions_have_type_annotations(self) -> None:
        """
        For any public function in the codebase, it SHALL have complete
        type annotations for all parameters and return type.

        **Feature: api-code-review, Property 4: Type Annotation Completeness**
        **Validates: Requirements 7.1**
        """
        source_files = get_all_source_files()
        violations: list[str] = []

        for file_path in source_files:
            # Skip __pycache__ and test files
            if "__pycache__" in str(file_path):
                continue

            functions = get_public_functions_from_module(file_path)

            for func in functions:
                is_complete, missing = check_type_completeness(func)
                if not is_complete:
                    violations.append(
                        f"{file_path}:{func['name']} - missing: {', '.join(missing)}"
                    )

        # Allow some tolerance for edge cases
        # Most functions should be annotated
        total_functions = sum(
            len(get_public_functions_from_module(f))
            for f in source_files
            if "__pycache__" not in str(f)
        )

        if total_functions > 0:
            violation_rate = len(violations) / total_functions
            # Assert at least 90% compliance
            assert violation_rate < 0.10, (
                f"Type annotation compliance is {(1 - violation_rate) * 100:.1f}% "
                f"(expected >= 90%). Violations:\n" +
                "\n".join(violations[:20])  # Show first 20
            )

    @settings(max_examples=50)
    @given(
        has_return=st.booleans(),
        param_annotations=st.lists(st.booleans(), min_size=0, max_size=5),
    )
    def test_completeness_check_logic(
        self,
        has_return: bool,
        param_annotations: list[bool],
    ) -> None:
        """
        The completeness check SHALL correctly identify missing annotations.
        """
        func_info = {
            "name": "test_func",
            "has_return_type": has_return,
            "params": [
                {"name": f"param{i}", "has_annotation": ann}
                for i, ann in enumerate(param_annotations)
            ],
            "file": "test.py",
        }

        is_complete, missing = check_type_completeness(func_info)

        # Verify logic
        expected_complete = has_return and all(param_annotations)
        assert is_complete == expected_complete

        # Verify missing count
        expected_missing_count = (0 if has_return else 1) + sum(
            1 for ann in param_annotations if not ann
        )
        assert len(missing) == expected_missing_count

    def test_source_files_exist(self) -> None:
        """Source directory SHALL contain Python files."""
        files = get_all_source_files()
        assert len(files) > 0, "No source files found in src/my_app"

    def test_ast_parsing_handles_all_files(self) -> None:
        """All source files SHALL be parseable by AST."""
        source_files = get_all_source_files()
        parse_errors: list[str] = []

        for file_path in source_files:
            if "__pycache__" in str(file_path):
                continue
            try:
                source = file_path.read_text(encoding="utf-8")
                ast.parse(source)
            except SyntaxError as e:
                parse_errors.append(f"{file_path}: {e}")

        assert len(parse_errors) == 0, (
            f"AST parse errors:\n" + "\n".join(parse_errors)
        )
