"""
RITE Framework Analysis Utilities.

**Feature: rite-framework-refactoring**
**Validates: Requirements 1.1, 2.1, 5.1**

This module provides utilities for analyzing code according to the RITE framework:
- Line counting for modularization analysis
- Class detection for one-class-per-file enforcement
- Import analysis for dependency management

Usage:
    from scripts.rite_analysis_utils import (
        count_file_lines,
        get_class_definitions,
        analyze_imports,
        generate_analysis_report,
    )
    
    # Analyze a single file
    analysis = analyze_file(Path("src/my_api/core/config.py"))
    
    # Generate full report
    report = generate_analysis_report(Path("src/my_api"))
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

# RITE Framework Thresholds
FILE_SIZE_SOFT_LIMIT = 300
FILE_SIZE_HARD_LIMIT = 400
SMALL_CLASS_EXCEPTION_LIMIT = 50


class ViolationType(Enum):
    """Types of RITE framework violations."""
    
    FILE_TOO_LARGE = "file_too_large"
    FILE_OVER_SOFT_LIMIT = "file_over_soft_limit"
    MULTIPLE_CLASSES = "multiple_classes"
    MISSING_MODULE_DOCSTRING = "missing_module_docstring"
    CIRCULAR_IMPORT = "circular_import"
    IMPORT_ORDER = "import_order"
    NAMING_CONVENTION = "naming_convention"


class Severity(Enum):
    """Severity levels for violations."""
    
    ERROR = "error"      # Must fix immediately
    WARNING = "warning"  # Should fix
    INFO = "info"        # Consider fixing


@dataclass
class Violation:
    """Represents a single RITE framework violation."""
    
    file: Path
    line: int
    violation_type: ViolationType
    severity: Severity
    message: str


@dataclass
class ClassInfo:
    """Information about a class definition."""
    
    name: str
    line_start: int
    line_end: int
    line_count: int


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    
    path: Path
    total_lines: int
    class_count: int
    classes: list[ClassInfo] = field(default_factory=list)
    has_module_docstring: bool = False
    violations: list[Violation] = field(default_factory=list)


@dataclass
class AnalysisReport:
    """Complete RITE framework analysis report."""
    
    files_analyzed: int = 0
    files_over_soft_limit: list[tuple[Path, int]] = field(default_factory=list)
    files_over_hard_limit: list[tuple[Path, int]] = field(default_factory=list)
    multi_class_files: list[tuple[Path, list[str]]] = field(default_factory=list)
    all_violations: list[Violation] = field(default_factory=list)


def count_file_lines(file_path: Path) -> int:
    """
    Count total lines in a file including comments and blank lines.
    
    Args:
        file_path: Path to the Python file.
        
    Returns:
        Total line count.
        
    Example:
        >>> count_file_lines(Path("src/my_api/main.py"))
        150
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        return len(content.splitlines())
    except (OSError, UnicodeDecodeError):
        return 0


def parse_file(file_path: Path) -> ast.AST | None:
    """
    Parse a Python file and return AST.
    
    Args:
        file_path: Path to the Python file.
        
    Returns:
        AST module or None if parsing fails.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        return ast.parse(content)
    except (SyntaxError, UnicodeDecodeError):
        return None


def get_class_definitions(tree: ast.AST) -> list[ClassInfo]:
    """
    Get all class definitions from AST with line information.
    
    Args:
        tree: Parsed AST module.
        
    Returns:
        List of ClassInfo objects.
        
    Example:
        >>> tree = parse_file(Path("src/my_api/domain/entities/item.py"))
        >>> classes = get_class_definitions(tree)
        >>> for cls in classes:
        ...     print(f"{cls.name}: {cls.line_count} lines")
    """
    classes = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            line_start = node.lineno
            line_end = node.end_lineno or node.lineno
            line_count = line_end - line_start + 1
            classes.append(ClassInfo(
                name=node.name,
                line_start=line_start,
                line_end=line_end,
                line_count=line_count,
            ))
    return classes


def has_module_docstring(tree: ast.AST) -> bool:
    """
    Check if module has a docstring.
    
    Args:
        tree: Parsed AST module.
        
    Returns:
        True if module has a docstring.
    """
    if not isinstance(tree, ast.Module) or not tree.body:
        return False
    first = tree.body[0]
    return (
        isinstance(first, ast.Expr)
        and isinstance(first.value, ast.Constant)
        and isinstance(first.value.value, str)
    )


def classify_import(module_name: str) -> str:
    """
    Classify import as stdlib, third-party, or local.
    
    Args:
        module_name: The module being imported.
        
    Returns:
        One of "stdlib", "third_party", or "local".
    """
    stdlib_modules = {
        "abc", "ast", "asyncio", "base64", "collections", "contextlib",
        "copy", "dataclasses", "datetime", "decimal", "enum", "functools",
        "hashlib", "hmac", "http", "importlib", "inspect", "io", "itertools",
        "json", "logging", "math", "os", "pathlib", "pickle", "random", "re",
        "secrets", "shutil", "socket", "sqlite3", "ssl", "string", "struct",
        "subprocess", "sys", "tempfile", "threading", "time", "traceback",
        "typing", "unittest", "urllib", "uuid", "warnings", "weakref", "xml",
        "zipfile", "zlib", "__future__", "types", "operator", "heapq",
        "bisect", "array", "queue", "multiprocessing", "concurrent",
    }
    
    top_module = module_name.split(".")[0]
    
    if top_module in stdlib_modules:
        return "stdlib"
    elif top_module in ("my_api", "src"):
        return "local"
    else:
        return "third_party"


def analyze_imports(tree: ast.AST) -> list[tuple[str, str, int]]:
    """
    Analyze imports in a module.
    
    Args:
        tree: Parsed AST module.
        
    Returns:
        List of (module_name, import_type, line_number) tuples.
        
    Example:
        >>> tree = parse_file(Path("src/my_api/main.py"))
        >>> imports = analyze_imports(tree)
        >>> for name, type_, line in imports:
        ...     print(f"{line}: {name} ({type_})")
    """
    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                import_type = classify_import(alias.name)
                imports.append((alias.name, import_type, node.lineno))
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                import_type = classify_import(node.module)
                imports.append((node.module, import_type, node.lineno))
    return imports


def to_snake_case(name: str) -> str:
    """
    Convert PascalCase to snake_case.
    
    Args:
        name: PascalCase string.
        
    Returns:
        snake_case string.
        
    Example:
        >>> to_snake_case("UserService")
        'user_service'
    """
    result = re.sub(r"([A-Z]+)([A-Z][a-z])", r"\1_\2", name)
    result = re.sub(r"([a-z\d])([A-Z])", r"\1_\2", result)
    return result.lower()


def analyze_file(file_path: Path) -> FileAnalysis:
    """
    Perform complete RITE framework analysis on a single file.
    
    Args:
        file_path: Path to the Python file.
        
    Returns:
        FileAnalysis object with all metrics and violations.
    """
    analysis = FileAnalysis(
        path=file_path,
        total_lines=count_file_lines(file_path),
        class_count=0,
    )
    
    tree = parse_file(file_path)
    if tree is None:
        return analysis
    
    # Analyze classes
    analysis.classes = get_class_definitions(tree)
    analysis.class_count = len(analysis.classes)
    analysis.has_module_docstring = has_module_docstring(tree)
    
    # Check for violations
    if analysis.total_lines > FILE_SIZE_HARD_LIMIT:
        analysis.violations.append(Violation(
            file=file_path,
            line=1,
            violation_type=ViolationType.FILE_TOO_LARGE,
            severity=Severity.ERROR,
            message=f"File has {analysis.total_lines} lines (max {FILE_SIZE_HARD_LIMIT})",
        ))
    elif analysis.total_lines > FILE_SIZE_SOFT_LIMIT:
        analysis.violations.append(Violation(
            file=file_path,
            line=1,
            violation_type=ViolationType.FILE_OVER_SOFT_LIMIT,
            severity=Severity.WARNING,
            message=f"File has {analysis.total_lines} lines (soft limit {FILE_SIZE_SOFT_LIMIT})",
        ))
    
    # Check for multiple classes
    if analysis.class_count > 1:
        total_class_lines = sum(cls.line_count for cls in analysis.classes)
        if total_class_lines > SMALL_CLASS_EXCEPTION_LIMIT:
            class_names = [cls.name for cls in analysis.classes]
            analysis.violations.append(Violation(
                file=file_path,
                line=1,
                violation_type=ViolationType.MULTIPLE_CLASSES,
                severity=Severity.WARNING,
                message=f"File contains {analysis.class_count} classes: {', '.join(class_names)}",
            ))
    
    # Check for module docstring
    if not analysis.has_module_docstring and file_path.stem != "__init__":
        analysis.violations.append(Violation(
            file=file_path,
            line=1,
            violation_type=ViolationType.MISSING_MODULE_DOCSTRING,
            severity=Severity.INFO,
            message="Missing module-level docstring",
        ))
    
    return analysis


def generate_analysis_report(src_root: Path) -> AnalysisReport:
    """
    Generate complete RITE framework analysis report for a directory.
    
    Args:
        src_root: Root directory to analyze.
        
    Returns:
        AnalysisReport with all findings.
        
    Example:
        >>> report = generate_analysis_report(Path("src/my_api"))
        >>> print(f"Files analyzed: {report.files_analyzed}")
        >>> print(f"Files over soft limit: {len(report.files_over_soft_limit)}")
    """
    report = AnalysisReport()
    
    for py_file in src_root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        
        report.files_analyzed += 1
        analysis = analyze_file(py_file)
        
        if analysis.total_lines > FILE_SIZE_HARD_LIMIT:
            report.files_over_hard_limit.append((py_file, analysis.total_lines))
        elif analysis.total_lines > FILE_SIZE_SOFT_LIMIT:
            report.files_over_soft_limit.append((py_file, analysis.total_lines))
        
        if analysis.class_count > 1:
            class_names = [cls.name for cls in analysis.classes]
            report.multi_class_files.append((py_file, class_names))
        
        report.all_violations.extend(analysis.violations)
    
    # Sort by severity
    report.files_over_soft_limit.sort(key=lambda x: x[1], reverse=True)
    report.files_over_hard_limit.sort(key=lambda x: x[1], reverse=True)
    
    return report


def print_report(report: AnalysisReport) -> None:
    """Print analysis report to console."""
    print("=" * 60)
    print("RITE Framework Analysis Report")
    print("=" * 60)
    print(f"\nFiles analyzed: {report.files_analyzed}")
    print(f"Files over soft limit ({FILE_SIZE_SOFT_LIMIT}): {len(report.files_over_soft_limit)}")
    print(f"Files over hard limit ({FILE_SIZE_HARD_LIMIT}): {len(report.files_over_hard_limit)}")
    print(f"Multi-class files: {len(report.multi_class_files)}")
    print(f"Total violations: {len(report.all_violations)}")
    
    if report.files_over_hard_limit:
        print(f"\n{'='*60}")
        print("FILES REQUIRING IMMEDIATE MODULARIZATION (>{} lines):".format(FILE_SIZE_HARD_LIMIT))
        for path, lines in report.files_over_hard_limit:
            print(f"  - {path.name}: {lines} lines")
    
    if report.files_over_soft_limit:
        print(f"\n{'='*60}")
        print("FILES FOR REVIEW (>{} lines):".format(FILE_SIZE_SOFT_LIMIT))
        for path, lines in report.files_over_soft_limit[:20]:
            print(f"  - {path.name}: {lines} lines")
    
    if report.multi_class_files:
        print(f"\n{'='*60}")
        print("MULTI-CLASS FILES:")
        for path, classes in report.multi_class_files[:20]:
            print(f"  - {path.name}: {', '.join(classes)}")


if __name__ == "__main__":
    import sys
    
    src_path = Path("src/my_api")
    if len(sys.argv) > 1:
        src_path = Path(sys.argv[1])
    
    report = generate_analysis_report(src_path)
    print_report(report)
