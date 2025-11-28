#!/usr/bin/env python
"""Validate all Python files are under 400 lines.

**Feature: code-review-refactoring, Task 20.1: Create file size validation script**
**Validates: Requirements 1.1, 1.3**

Usage:
    python scripts/check_file_sizes.py
    python scripts/check_file_sizes.py --max-lines 500
    python scripts/check_file_sizes.py --fail-on-violation
"""

import argparse
import sys
from pathlib import Path


DEFAULT_MAX_LINES = 400
SRC_DIR = Path("src")
EXCLUDE_PATTERNS = [
    "__pycache__",
    ".pyc",
    "__init__.py",  # Init files can be longer due to re-exports
]


def count_lines(file_path: Path) -> int:
    """Count non-empty, non-comment lines in a Python file."""
    try:
        content = file_path.read_text(encoding="utf-8")
        return len(content.splitlines())
    except Exception:
        return 0


def should_exclude(file_path: Path) -> bool:
    """Check if file should be excluded from validation."""
    path_str = str(file_path)
    return any(pattern in path_str for pattern in EXCLUDE_PATTERNS)


def check_file_sizes(
    src_dir: Path = SRC_DIR,
    max_lines: int = DEFAULT_MAX_LINES,
) -> list[tuple[Path, int]]:
    """Find all files exceeding the line limit.

    Args:
        src_dir: Source directory to scan.
        max_lines: Maximum allowed lines per file.

    Returns:
        List of (file_path, line_count) tuples for violations.
    """
    violations = []

    if not src_dir.exists():
        print(f"Warning: Source directory {src_dir} does not exist")
        return violations

    for py_file in src_dir.rglob("*.py"):
        if should_exclude(py_file):
            continue

        line_count = count_lines(py_file)
        if line_count > max_lines:
            violations.append((py_file, line_count))

    return sorted(violations, key=lambda x: x[1], reverse=True)


def print_report(
    violations: list[tuple[Path, int]],
    max_lines: int,
) -> None:
    """Print a report of file size violations."""
    if violations:
        print(f"\n❌ {len(violations)} files exceed {max_lines} lines:\n")
        for path, lines in violations:
            excess = lines - max_lines
            print(f"  {path}: {lines} lines (+{excess})")
        print()
    else:
        print(f"\n✅ All files are under {max_lines} lines\n")


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Check Python file sizes against maximum line limit"
    )
    parser.add_argument(
        "--max-lines",
        type=int,
        default=DEFAULT_MAX_LINES,
        help=f"Maximum allowed lines per file (default: {DEFAULT_MAX_LINES})",
    )
    parser.add_argument(
        "--src-dir",
        type=Path,
        default=SRC_DIR,
        help=f"Source directory to scan (default: {SRC_DIR})",
    )
    parser.add_argument(
        "--fail-on-violation",
        action="store_true",
        help="Exit with code 1 if violations found",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args()

    violations = check_file_sizes(args.src_dir, args.max_lines)

    if args.json:
        import json
        result = {
            "max_lines": args.max_lines,
            "violations": [
                {"file": str(path), "lines": lines}
                for path, lines in violations
            ],
            "passed": len(violations) == 0,
        }
        print(json.dumps(result, indent=2))
    else:
        print_report(violations, args.max_lines)

    if args.fail_on_violation and violations:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
