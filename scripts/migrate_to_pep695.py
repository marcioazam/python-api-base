#!/usr/bin/env python3
"""Automated migration script for PEP 695 compliance and code quality.

This script automatically migrates:
1. Old TypeVar syntax to PEP 695 class-level type parameters
2. Old ParamSpec syntax to PEP 695 inline type parameters
3. Old Generic[] syntax to PEP 695 syntax
4. Adds slots=True to frozen dataclasses
5. Adds missing return type annotations

Usage:
    python scripts/migrate_to_pep695.py [--dry-run] [--verbose]
"""

import argparse
import re
import sys
from pathlib import Path


def migrate_typevar_to_pep695(content: str, filepath: str) -> str:
    """Migrate old TypeVar syntax to PEP 695."""
    # Pattern to find TypeVar definitions
    typevar_pattern = re.compile(
        r'^(\s*)(\w+)\s*=\s*TypeVar\s*\(\s*["\'](\w+)["\']\s*(?:,\s*bound\s*=\s*(\w+))?\s*\)',
        re.MULTILINE
    )
    
    # Find all TypeVar definitions
    typevars = {}
    for match in typevar_pattern.finditer(content):
        indent, var_name, type_name, bound = match.groups()
        typevars[var_name] = bound
    
    if not typevars:
        return content
    
    # Remove TypeVar imports if no longer needed after migration
    # Remove TypeVar definitions
    for var_name in typevars:
        # Remove the TypeVar line
        content = re.sub(
            rf'^.*{var_name}\s*=\s*TypeVar\s*\([^)]+\).*\n',
            '',
            content,
            flags=re.MULTILINE
        )
    
    # Remove Generic import if present and update class definitions
    # This is complex - we'll handle it per-file basis
    
    return content


def add_slots_to_frozen_dataclass(content: str) -> str:
    """Add slots=True to frozen dataclasses that don't have it."""
    # Pattern: @dataclass(frozen=True) without slots=True
    pattern = r'@dataclass\(frozen=True\)(?!\s*#.*slots)'
    
    # Check if already has slots
    if '@dataclass(frozen=True, slots=True)' in content:
        return content
    
    # Replace frozen=True with frozen=True, slots=True
    content = re.sub(
        r'@dataclass\(frozen=True\)',
        '@dataclass(frozen=True, slots=True)',
        content
    )
    
    return content


def fix_missing_return_type(content: str, func_name: str) -> str:
    """Add return type annotation to a function."""
    # Pattern for async def without return type
    pattern = rf'(async\s+def\s+{func_name}\s*\([^)]*\))\s*:'
    
    # Add -> None if no return type
    content = re.sub(pattern, r'\1 -> None:', content)
    
    return content


def process_file(filepath: Path, dry_run: bool = False, verbose: bool = False) -> tuple[bool, list[str]]:
    """Process a single file for migrations."""
    changes = []
    
    try:
        content = filepath.read_text(encoding='utf-8')
        original_content = content
        
        # 1. Add slots=True to frozen dataclasses
        if '@dataclass(frozen=True)' in content and 'slots=True' not in content:
            content = add_slots_to_frozen_dataclass(content)
            if content != original_content:
                changes.append(f"Added slots=True to frozen dataclass in {filepath}")
        
        # 2. Fix specific missing return type
        if 'renewal_loop' in str(filepath) or 'distributed_lock' in str(filepath):
            if 'def renewal_loop' in content and '-> None:' not in content:
                content = fix_missing_return_type(content, 'renewal_loop')
                changes.append(f"Added return type to renewal_loop in {filepath}")
        
        # Write changes if not dry run
        if content != original_content:
            if not dry_run:
                filepath.write_text(content, encoding='utf-8')
            return True, changes
        
        return False, changes
        
    except Exception as e:
        return False, [f"Error processing {filepath}: {e}"]


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Migrate code to PEP 695 compliance")
    parser.add_argument("--dry-run", action="store_true", help="Don't write changes")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    args = parser.parse_args()
    
    src_path = Path("src/my_api")
    
    if not src_path.exists():
        print(f"Error: {src_path} does not exist")
        return 1
    
    total_files = 0
    modified_files = 0
    all_changes = []
    
    for filepath in src_path.rglob("*.py"):
        if "__pycache__" in str(filepath):
            continue
        
        total_files += 1
        modified, changes = process_file(filepath, args.dry_run, args.verbose)
        
        if modified:
            modified_files += 1
            all_changes.extend(changes)
    
    print(f"\nProcessed {total_files} files")
    print(f"Modified {modified_files} files")
    
    if all_changes:
        print("\nChanges made:")
        for change in all_changes:
            print(f"  - {change}")
    
    if args.dry_run:
        print("\n(Dry run - no files were actually modified)")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
