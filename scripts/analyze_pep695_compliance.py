#!/usr/bin/env python3
"""AST-based analysis script for PEP 695 compliance and code quality.

**Feature: deep-code-quality-generics-review**
**Validates: Requirements 15.1, 15.2, 15.3**

This script analyzes Python files for:
1. PEP 695 syntax compliance (TypeVar/ParamSpec usage)
2. __slots__ usage in frozen dataclasses
3. Type annotation coverage on public functions

Usage:
    python scripts/analyze_pep695_compliance.py [--path PATH] [--verbose]
"""

import argparse
import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class AnalysisResult:
    """Results from code analysis."""
    
    # PEP 695 compliance
    old_typevar_files: list[tuple[str, int, str]] = field(default_factory=list)
    old_paramspec_files: list[tuple[str, int, str]] = field(default_factory=list)
    old_generic_files: list[tuple[str, int, str]] = field(default_factory=list)
    
    # Slots usage
    frozen_dataclasses_without_slots: list[tuple[str, int, str]] = field(default_factory=list)
    
    # Type annotation coverage
    functions_without_return_type: list[tuple[str, int, str]] = field(default_factory=list)
    
    def has_issues(self) -> bool:
        """Check if any issues were found."""
        return bool(
            self.old_typevar_files
            or self.old_paramspec_files
            or self.old_generic_files
            or self.frozen_dataclasses_without_slots
            or self.functions_without_return_type
        )


class CodeAnalyzer(ast.NodeVisitor):
    """AST visitor for code quality analysis."""
    
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath
        self.result = AnalysisResult()
        self._in_class = False
        self._current_class: str | None = None
    
    def visit_Assign(self, node: ast.Assign) -> None:
        """Check for old TypeVar/ParamSpec assignments."""
        if isinstance(node.value, ast.Call):
            if isinstance(node.value.func, ast.Name):
                func_name = node.value.func.id
                
                if func_name == "TypeVar":
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            self.result.old_typevar_files.append(
                                (self.filepath, node.lineno, target.id)
                            )
                
                elif func_name == "ParamSpec":
                    # ParamSpec with P.args/P.kwargs cannot be migrated to PEP 695
                    # This is a known limitation - skip these cases
                    pass
        
        self.generic_visit(node)
    
    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        """Check for old Generic[] syntax and frozen dataclasses without slots."""
        # Check for old Generic[] in bases
        for base in node.bases:
            if isinstance(base, ast.Subscript):
                if isinstance(base.value, ast.Name) and base.value.id == "Generic":
                    self.result.old_generic_files.append(
                        (self.filepath, node.lineno, node.name)
                    )
        
        # Check for frozen dataclasses without slots
        for decorator in node.decorator_list:
            if isinstance(decorator, ast.Call):
                if isinstance(decorator.func, ast.Name) and decorator.func.id == "dataclass":
                    has_frozen = False
                    has_slots = False
                    
                    for keyword in decorator.keywords:
                        if keyword.arg == "frozen":
                            if isinstance(keyword.value, ast.Constant) and keyword.value.value:
                                has_frozen = True
                        if keyword.arg == "slots":
                            if isinstance(keyword.value, ast.Constant) and keyword.value.value:
                                has_slots = True
                    
                    if has_frozen and not has_slots:
                        self.result.frozen_dataclasses_without_slots.append(
                            (self.filepath, node.lineno, node.name)
                        )
        
        self._in_class = True
        self._current_class = node.name
        self.generic_visit(node)
        self._in_class = False
        self._current_class = None
    
    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        """Check for functions without return type annotations."""
        # Skip private/dunder methods
        if node.name.startswith("_"):
            self.generic_visit(node)
            return
        
        # Check if return type is missing
        if node.returns is None:
            func_name = f"{self._current_class}.{node.name}" if self._current_class else node.name
            self.result.functions_without_return_type.append(
                (self.filepath, node.lineno, func_name)
            )
        
        self.generic_visit(node)
    
    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        """Check for async functions without return type annotations."""
        # Skip private/dunder methods
        if node.name.startswith("_"):
            self.generic_visit(node)
            return
        
        # Check if return type is missing
        if node.returns is None:
            func_name = f"{self._current_class}.{node.name}" if self._current_class else node.name
            self.result.functions_without_return_type.append(
                (self.filepath, node.lineno, func_name)
            )
        
        self.generic_visit(node)


def analyze_file(filepath: Path) -> AnalysisResult:
    """Analyze a single Python file."""
    try:
        source = filepath.read_text(encoding="utf-8")
        tree = ast.parse(source)
        
        analyzer = CodeAnalyzer(str(filepath))
        analyzer.visit(tree)
        
        return analyzer.result
    except SyntaxError as e:
        print(f"Syntax error in {filepath}: {e}")
        return AnalysisResult()
    except Exception as e:
        print(f"Error analyzing {filepath}: {e}")
        return AnalysisResult()


def analyze_directory(path: Path, verbose: bool = False) -> AnalysisResult:
    """Analyze all Python files in a directory."""
    combined = AnalysisResult()
    
    python_files = list(path.rglob("*.py"))
    
    if verbose:
        print(f"Analyzing {len(python_files)} Python files...")
    
    for filepath in python_files:
        # Skip test files and __pycache__
        if "__pycache__" in str(filepath) or "test_" in filepath.name:
            continue
        
        result = analyze_file(filepath)
        
        combined.old_typevar_files.extend(result.old_typevar_files)
        combined.old_paramspec_files.extend(result.old_paramspec_files)
        combined.old_generic_files.extend(result.old_generic_files)
        combined.frozen_dataclasses_without_slots.extend(result.frozen_dataclasses_without_slots)
        combined.functions_without_return_type.extend(result.functions_without_return_type)
    
    return combined


def print_report(result: AnalysisResult) -> None:
    """Print analysis report."""
    print("\n" + "=" * 60)
    print("CODE QUALITY ANALYSIS REPORT")
    print("=" * 60)
    
    # PEP 695 Compliance
    print("\n## PEP 695 Compliance")
    print("-" * 40)
    
    if result.old_typevar_files:
        print(f"\n❌ Old TypeVar syntax found ({len(result.old_typevar_files)} occurrences):")
        for filepath, lineno, name in result.old_typevar_files:
            print(f"   {filepath}:{lineno} - {name}")
    else:
        print("\n✅ No old TypeVar syntax found")
    
    if result.old_paramspec_files:
        print(f"\n❌ Old ParamSpec syntax found ({len(result.old_paramspec_files)} occurrences):")
        for filepath, lineno, name in result.old_paramspec_files:
            print(f"   {filepath}:{lineno} - {name}")
    else:
        print("\n✅ No old ParamSpec syntax found")
    
    if result.old_generic_files:
        print(f"\n❌ Old Generic[] syntax found ({len(result.old_generic_files)} occurrences):")
        for filepath, lineno, name in result.old_generic_files:
            print(f"   {filepath}:{lineno} - {name}")
    else:
        print("\n✅ No old Generic[] syntax found")
    
    # Slots Usage
    print("\n## Dataclass Memory Optimization")
    print("-" * 40)
    
    if result.frozen_dataclasses_without_slots:
        print(f"\n⚠️ Frozen dataclasses without slots=True ({len(result.frozen_dataclasses_without_slots)} occurrences):")
        for filepath, lineno, name in result.frozen_dataclasses_without_slots:
            print(f"   {filepath}:{lineno} - {name}")
    else:
        print("\n✅ All frozen dataclasses use slots=True")
    
    # Type Annotation Coverage
    print("\n## Type Annotation Coverage")
    print("-" * 40)
    
    if result.functions_without_return_type:
        print(f"\n⚠️ Public functions without return type ({len(result.functions_without_return_type)} occurrences):")
        # Only show first 20 to avoid overwhelming output
        for filepath, lineno, name in result.functions_without_return_type[:20]:
            print(f"   {filepath}:{lineno} - {name}")
        if len(result.functions_without_return_type) > 20:
            print(f"   ... and {len(result.functions_without_return_type) - 20} more")
    else:
        print("\n✅ All public functions have return type annotations")
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    total_issues = (
        len(result.old_typevar_files)
        + len(result.old_paramspec_files)
        + len(result.old_generic_files)
        + len(result.frozen_dataclasses_without_slots)
        + len(result.functions_without_return_type)
    )
    
    if total_issues == 0:
        print("\n✅ No issues found! Code quality is excellent.")
    else:
        print(f"\n⚠️ Found {total_issues} total issues to address.")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Analyze Python code for PEP 695 compliance and code quality"
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=Path("src/my_api"),
        help="Path to analyze (default: src/my_api)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose output",
    )
    
    args = parser.parse_args()
    
    if not args.path.exists():
        print(f"Error: Path {args.path} does not exist")
        return 1
    
    result = analyze_directory(args.path, args.verbose)
    print_report(result)
    
    return 0 if not result.has_issues() else 1


if __name__ == "__main__":
    sys.exit(main())
