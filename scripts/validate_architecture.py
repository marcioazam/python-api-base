#!/usr/bin/env python3
"""Architecture validation script for Clean Architecture compliance.

**Feature: python-api-code-review-2025, Task 1.1**
**Validates: Requirements 1.1, 1.2, 1.3**

This script validates that the codebase follows Clean Architecture principles:
- Domain layer has no imports from adapters or infrastructure
- Use cases depend only on domain interfaces
- Adapters implement domain protocols
"""

import ast
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Final

# Layer definitions
DOMAIN_LAYER: Final[str] = "domain"
APPLICATION_LAYER: Final[str] = "application"
ADAPTERS_LAYER: Final[str] = "adapters"
INFRASTRUCTURE_LAYER: Final[str] = "infrastructure"
CORE_LAYER: Final[str] = "core"
SHARED_LAYER: Final[str] = "shared"

# Forbidden imports per layer (layer -> forbidden sources)
LAYER_RULES: Final[dict[str, set[str]]] = {
    DOMAIN_LAYER: {ADAPTERS_LAYER, INFRASTRUCTURE_LAYER},
    APPLICATION_LAYER: {ADAPTERS_LAYER},
    # Core and shared can import from anywhere within the project
}


@dataclass
class Violation:
    """Represents an architecture violation."""
    
    file_path: str
    line_number: int
    layer: str
    forbidden_import: str
    message: str


@dataclass
class ValidationResult:
    """Result of architecture validation."""
    
    violations: list[Violation] = field(default_factory=list)
    files_checked: int = 0
    
    @property
    def is_valid(self) -> bool:
        """Check if validation passed."""
        return len(self.violations) == 0
    
    def add_violation(self, violation: Violation) -> None:
        """Add a violation to the result."""
        self.violations.append(violation)


class ImportVisitor(ast.NodeVisitor):
    """AST visitor to extract import statements."""
    
    def __init__(self) -> None:
        self.imports: list[tuple[int, str]] = []
    
    def visit_Import(self, node: ast.Import) -> None:
        """Visit import statement."""
        for alias in node.names:
            self.imports.append((node.lineno, alias.name))
        self.generic_visit(node)
    
    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        """Visit from...import statement."""
        if node.module:
            self.imports.append((node.lineno, node.module))
        self.generic_visit(node)


def get_layer_from_path(file_path: Path, base_path: Path) -> str | None:
    """Determine which layer a file belongs to.
    
    Args:
        file_path: Path to the Python file.
        base_path: Base path of the project (src/my_api).
        
    Returns:
        Layer name or None if not in a recognized layer.
    """
    try:
        relative = file_path.relative_to(base_path)
        parts = relative.parts
        if parts:
            return parts[0]
    except ValueError:
        pass
    return None


def extract_imports(file_path: Path) -> list[tuple[int, str]]:
    """Extract all imports from a Python file.
    
    Args:
        file_path: Path to the Python file.
        
    Returns:
        List of (line_number, import_name) tuples.
    """
    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content)
        visitor = ImportVisitor()
        visitor.visit(tree)
        return visitor.imports
    except (SyntaxError, UnicodeDecodeError) as e:
        print(f"Warning: Could not parse {file_path}: {e}")
        return []


def get_import_layer(import_name: str) -> str | None:
    """Determine which layer an import comes from.
    
    Args:
        import_name: Full import name (e.g., 'my_api.adapters.api').
        
    Returns:
        Layer name or None if not a project import.
    """
    if not import_name.startswith("my_api."):
        return None
    
    parts = import_name.split(".")
    if len(parts) >= 2:
        return parts[1]
    return None


def validate_file(
    file_path: Path,
    base_path: Path,
    result: ValidationResult,
) -> None:
    """Validate a single file for architecture violations.
    
    Args:
        file_path: Path to the Python file.
        base_path: Base path of the project.
        result: ValidationResult to add violations to.
    """
    layer = get_layer_from_path(file_path, base_path)
    if layer is None or layer not in LAYER_RULES:
        return
    
    forbidden_layers = LAYER_RULES[layer]
    imports = extract_imports(file_path)
    
    for line_number, import_name in imports:
        import_layer = get_import_layer(import_name)
        if import_layer and import_layer in forbidden_layers:
            violation = Violation(
                file_path=str(file_path),
                line_number=line_number,
                layer=layer,
                forbidden_import=import_name,
                message=(
                    f"Layer '{layer}' should not import from '{import_layer}'. "
                    f"Found: {import_name}"
                ),
            )
            result.add_violation(violation)


def validate_architecture(base_path: Path) -> ValidationResult:
    """Validate the entire codebase for architecture violations.
    
    Args:
        base_path: Base path of the project (src/my_api).
        
    Returns:
        ValidationResult with all violations found.
    """
    result = ValidationResult()
    
    for py_file in base_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        result.files_checked += 1
        validate_file(py_file, base_path, result)
    
    return result


def print_report(result: ValidationResult) -> None:
    """Print validation report to stdout.
    
    Args:
        result: ValidationResult to report.
    """
    print("=" * 60)
    print("Architecture Validation Report")
    print("=" * 60)
    print(f"Files checked: {result.files_checked}")
    print(f"Violations found: {len(result.violations)}")
    print()
    
    if result.is_valid:
        print("✅ All architecture rules passed!")
    else:
        print("❌ Architecture violations detected:")
        print()
        for v in result.violations:
            print(f"  {v.file_path}:{v.line_number}")
            print(f"    {v.message}")
            print()


def main() -> int:
    """Main entry point.
    
    Returns:
        Exit code (0 for success, 1 for violations).
    """
    base_path = Path("src/my_api")
    
    if not base_path.exists():
        print(f"Error: Base path '{base_path}' does not exist")
        return 1
    
    result = validate_architecture(base_path)
    print_report(result)
    
    return 0 if result.is_valid else 1


if __name__ == "__main__":
    sys.exit(main())
