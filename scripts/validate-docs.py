#!/usr/bin/env python3
"""Documentation validation script.

Validates ADR format, Mermaid syntax, and code references in documentation.
"""

import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class ValidationErrorType(Enum):
    """Types of validation errors."""

    MISSING_SECTION = "missing_section"
    INVALID_LINK = "invalid_link"
    INVALID_MERMAID = "invalid_mermaid"
    MISSING_HISTORY = "missing_history"


@dataclass
class ValidationError:
    """Represents a validation error."""

    file: Path
    error_type: ValidationErrorType
    message: str
    line: int | None = None


ADR_REQUIRED_SECTIONS = [
    "# ADR-",
    "## Status",
    "## Context",
    "## Decision",
    "## Consequences",
    "## Alternatives",
]

ADR_STATUS_VALUES = ["Proposed", "Accepted", "Deprecated", "Superseded"]

MERMAID_DIAGRAM_TYPES = [
    "graph",
    "flowchart",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "pie",
    "gitGraph",
]


def validate_adr_format(adr_file: Path) -> list[ValidationError]:
    """Validate ADR file format.

    Args:
        adr_file: Path to ADR file

    Returns:
        List of validation errors
    """
    errors: list[ValidationError] = []
    content = adr_file.read_text(encoding="utf-8")

    # Check required sections
    for section in ADR_REQUIRED_SECTIONS:
        if section not in content:
            errors.append(
                ValidationError(
                    file=adr_file,
                    error_type=ValidationErrorType.MISSING_SECTION,
                    message=f"Missing required section: {section}",
                )
            )

    # Check status value
    status_match = re.search(r"## Status\s*\n\s*(\w+)", content)
    if status_match:
        status = status_match.group(1)
        if status not in ADR_STATUS_VALUES:
            errors.append(
                ValidationError(
                    file=adr_file,
                    error_type=ValidationErrorType.MISSING_SECTION,
                    message=f"Invalid status value: {status}. Must be one of {ADR_STATUS_VALUES}",
                )
            )

        # Check history for non-Proposed ADRs
        if status != "Proposed" and "## History" not in content:
            errors.append(
                ValidationError(
                    file=adr_file,
                    error_type=ValidationErrorType.MISSING_HISTORY,
                    message="ADR with non-Proposed status must have History section",
                )
            )

    return errors


def validate_adr_links(adr_file: Path, project_root: Path) -> list[ValidationError]:
    """Validate code references in ADR file.

    Args:
        adr_file: Path to ADR file
        project_root: Root directory of the project

    Returns:
        List of validation errors
    """
    errors: list[ValidationError] = []
    content = adr_file.read_text(encoding="utf-8")

    # Find all src/ references
    src_refs = re.findall(r"src/[\w/]+(?:\.py)?", content)

    for ref in src_refs:
        ref_path = project_root / ref
        # Check if it's a file or directory
        if not ref_path.exists() and not ref_path.with_suffix(".py").exists():
            # Check if it's a directory
            if not (project_root / ref.rstrip("/")).is_dir():
                errors.append(
                    ValidationError(
                        file=adr_file,
                        error_type=ValidationErrorType.INVALID_LINK,
                        message=f"Invalid code reference: {ref}",
                    )
                )

    return errors


def validate_mermaid_syntax(doc_file: Path) -> list[ValidationError]:
    """Validate Mermaid diagram syntax in documentation file.

    Args:
        doc_file: Path to documentation file

    Returns:
        List of validation errors
    """
    errors: list[ValidationError] = []
    content = doc_file.read_text(encoding="utf-8")

    # Find all mermaid code blocks
    mermaid_blocks = re.findall(r"```mermaid\s*(.*?)```", content, re.DOTALL)

    for i, block in enumerate(mermaid_blocks):
        block = block.strip()
        if not block:
            errors.append(
                ValidationError(
                    file=doc_file,
                    error_type=ValidationErrorType.INVALID_MERMAID,
                    message=f"Empty Mermaid block #{i + 1}",
                )
            )
            continue

        # Check if diagram type is valid
        first_line = block.split("\n")[0].strip()
        diagram_type = first_line.split()[0] if first_line else ""

        # Handle special cases
        if diagram_type in ["graph", "flowchart"]:
            # Must have direction (TB, LR, etc.)
            if len(first_line.split()) < 2:
                errors.append(
                    ValidationError(
                        file=doc_file,
                        error_type=ValidationErrorType.INVALID_MERMAID,
                        message=f"Mermaid {diagram_type} missing direction in block #{i + 1}",
                    )
                )
        elif diagram_type not in MERMAID_DIAGRAM_TYPES:
            # Check if it starts with a valid type
            valid_start = any(block.startswith(dt) for dt in MERMAID_DIAGRAM_TYPES)
            if not valid_start:
                errors.append(
                    ValidationError(
                        file=doc_file,
                        error_type=ValidationErrorType.INVALID_MERMAID,
                        message=f"Unknown Mermaid diagram type in block #{i + 1}: {diagram_type}",
                    )
                )

    return errors


def validate_documentation(project_root: Path) -> list[ValidationError]:
    """Validate all documentation files.

    Args:
        project_root: Root directory of the project

    Returns:
        List of all validation errors
    """
    errors: list[ValidationError] = []
    docs_dir = project_root / "docs"

    # Validate ADRs
    adr_dir = docs_dir / "adr"
    if adr_dir.exists():
        for adr_file in adr_dir.glob("ADR-*.md"):
            errors.extend(validate_adr_format(adr_file))
            errors.extend(validate_adr_links(adr_file, project_root))

    # Validate Mermaid in all docs
    for doc_file in docs_dir.rglob("*.md"):
        errors.extend(validate_mermaid_syntax(doc_file))

    return errors


def main() -> int:
    """Main entry point.

    Returns:
        Exit code (0 for success, 1 for validation errors)
    """
    project_root = Path(__file__).parent.parent

    print("Validating documentation...")
    errors = validate_documentation(project_root)

    if errors:
        print(f"\nFound {len(errors)} validation error(s):\n")
        for error in errors:
            print(f"  [{error.error_type.value}] {error.file}: {error.message}")
        return 1

    print("All documentation is valid!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
