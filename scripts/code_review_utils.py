"""
Code Review Utilities.

**Feature: comprehensive-code-review**
**Validates: Requirements 3.1, 3.2, 3.4**

Provides AST parsing helpers, line counting, and complexity calculation
for code review analysis.
"""

from __future__ import annotations

import ast
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator


class Severity(Enum):
    """Finding severity levels."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Category(Enum):
    """Finding categories."""

    SIZE = "size"
    COMPLEXITY = "complexity"
    ARCHITECTURE = "architecture"
    DOCUMENTATION = "documentation"
    SECURITY = "security"
    NAMING = "naming"


@dataclass
class Finding:
    """Represents a code review finding."""

    file: Path
    line: int
    rule: str
    severity: Severity
    category: Category
    message: str

    def __str__(self) -> str:
        return f"{self.file}:{self.line} [{self.severity.value}] {self.message}"


def parse_file(file_path: Path) -> ast.AST | None:
    """Parse a Python file and return AST."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return None


def count_lines(file_path: Path) -> int:
    """Count total lines in a file."""
    try:
        return len(file_path.read_text(encoding="utf-8").splitlines())
    except (OSError, UnicodeDecodeError):
        return 0


def count_function_lines(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count lines in a function body."""
    if not node.body:
        return 0
    first_line = node.body[0].lineno
    last_line = node.body[-1].end_lineno or node.body[-1].lineno
    return last_line - first_line + 1


def count_class_lines(node: ast.ClassDef) -> int:
    """Count lines in a class definition."""
    if not node.body:
        return 0
    return (node.end_lineno or node.lineno) - node.lineno + 1


def calculate_nesting_depth(node: ast.AST, current_depth: int = 0) -> int:
    """Calculate maximum nesting depth in a node."""
    max_depth = current_depth
    nesting_nodes = (
        ast.If,
        ast.For,
        ast.While,
        ast.With,
        ast.Try,
        ast.AsyncFor,
        ast.AsyncWith,
    )

    for child in ast.iter_child_nodes(node):
        if isinstance(child, nesting_nodes):
            child_depth = calculate_nesting_depth(child, current_depth + 1)
            max_depth = max(max_depth, child_depth)
        else:
            child_depth = calculate_nesting_depth(child, current_depth)
            max_depth = max(max_depth, child_depth)

    return max_depth


def calculate_cyclomatic_complexity(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> int:
    """Calculate cyclomatic complexity of a function."""
    complexity = 1

    for child in ast.walk(node):
        if isinstance(child, (ast.If, ast.While, ast.For, ast.AsyncFor)):
            complexity += 1
        elif isinstance(child, ast.BoolOp):
            complexity += len(child.values) - 1
        elif isinstance(child, ast.ExceptHandler):
            complexity += 1
        elif isinstance(child, (ast.Assert, ast.comprehension)):
            complexity += 1

    return complexity


def count_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count function parameters excluding self/cls."""
    args = node.args
    count = len(args.args) + len(args.posonlyargs) + len(args.kwonlyargs)

    if args.args and args.args[0].arg in ("self", "cls"):
        count -= 1

    return count


def get_imports(tree: ast.AST) -> list[str]:
    """Extract all imports from AST."""
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def has_docstring(
    node: ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef | ast.Module,
) -> bool:
    """Check if node has a docstring."""
    if not node.body:
        return False
    first = node.body[0]
    return (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    )


def analyze_file(file_path: Path, thresholds: dict | None = None) -> list[Finding]:
    """Analyze a single file and return findings."""
    if thresholds is None:
        thresholds = {
            "max_function_lines": 75,
            "max_class_lines": 400,
            "max_nesting": 4,
            "max_complexity": 15,
            "max_parameters": 6,
        }

    findings = []
    tree = parse_file(file_path)

    if tree is None:
        findings.append(
            Finding(
                file=file_path,
                line=0,
                rule="parse-error",
                severity=Severity.ERROR,
                category=Category.SIZE,
                message="Could not parse file",
            )
        )
        return findings

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            lines = count_function_lines(node)
            if lines > thresholds["max_function_lines"]:
                findings.append(
                    Finding(
                        file=file_path,
                        line=node.lineno,
                        rule="function-too-long",
                        severity=Severity.WARNING,
                        category=Category.SIZE,
                        message=f"Function '{node.name}' has {lines} lines (max: {thresholds['max_function_lines']})",
                    )
                )

            complexity = calculate_cyclomatic_complexity(node)
            if complexity > thresholds["max_complexity"]:
                findings.append(
                    Finding(
                        file=file_path,
                        line=node.lineno,
                        rule="high-complexity",
                        severity=Severity.WARNING,
                        category=Category.COMPLEXITY,
                        message=f"Function '{node.name}' has complexity {complexity} (max: {thresholds['max_complexity']})",
                    )
                )

            nesting = calculate_nesting_depth(node)
            if nesting > thresholds["max_nesting"]:
                findings.append(
                    Finding(
                        file=file_path,
                        line=node.lineno,
                        rule="deep-nesting",
                        severity=Severity.WARNING,
                        category=Category.COMPLEXITY,
                        message=f"Function '{node.name}' has nesting depth {nesting} (max: {thresholds['max_nesting']})",
                    )
                )

            params = count_parameters(node)
            if params > thresholds["max_parameters"]:
                findings.append(
                    Finding(
                        file=file_path,
                        line=node.lineno,
                        rule="too-many-parameters",
                        severity=Severity.INFO,
                        category=Category.SIZE,
                        message=f"Function '{node.name}' has {params} parameters (max: {thresholds['max_parameters']})",
                    )
                )

        elif isinstance(node, ast.ClassDef):
            lines = count_class_lines(node)
            if lines > thresholds["max_class_lines"]:
                findings.append(
                    Finding(
                        file=file_path,
                        line=node.lineno,
                        rule="class-too-long",
                        severity=Severity.WARNING,
                        category=Category.SIZE,
                        message=f"Class '{node.name}' has {lines} lines (max: {thresholds['max_class_lines']})",
                    )
                )

    return findings


def analyze_directory(directory: Path, thresholds: dict | None = None) -> list[Finding]:
    """Analyze all Python files in a directory."""
    findings = []
    for py_file in directory.rglob("*.py"):
        if "__pycache__" not in str(py_file):
            findings.extend(analyze_file(py_file, thresholds))
    return findings


def print_report(findings: list[Finding]) -> None:
    """Print a formatted report of findings."""
    if not findings:
        print("No issues found!")
        return

    by_severity = {s: [] for s in Severity}
    for f in findings:
        by_severity[f.severity].append(f)

    print(f"\n=== Code Review Report ===")
    print(f"Total findings: {len(findings)}")
    print(f"  Errors: {len(by_severity[Severity.ERROR])}")
    print(f"  Warnings: {len(by_severity[Severity.WARNING])}")
    print(f"  Info: {len(by_severity[Severity.INFO])}")
    print()

    for severity in [Severity.ERROR, Severity.WARNING, Severity.INFO]:
        if by_severity[severity]:
            print(f"\n--- {severity.value.upper()} ---")
            for f in by_severity[severity]:
                print(f"  {f}")


if __name__ == "__main__":
    src_path = Path(__file__).parent.parent / "src" / "my_api"
    findings = analyze_directory(src_path)
    print_report(findings)
