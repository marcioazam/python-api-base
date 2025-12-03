#!/usr/bin/env python3
"""Documentation validation script.

Validates:
- Internal link validity
- Code example syntax
- Documentation coverage
"""

import ast
import re
import sys
from pathlib import Path
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Validation result."""
    is_valid: bool
    errors: list[str]
    warnings: list[str]


def find_markdown_files(docs_dir: Path) -> list[Path]:
    """Find all markdown files in docs directory."""
    return list(docs_dir.rglob("*.md"))


def extract_internal_links(content: str) -> list[str]:
    """Extract internal markdown links from content."""
    # Match [text](path.md) or [text](../path.md)
    pattern = r'\[([^\]]+)\]\(([^)]+\.md[^)]*)\)'
    matches = re.findall(pattern, content)
    return [match[1].split('#')[0] for match in matches]


def validate_internal_links(docs_dir: Path) -> ValidationResult:
    """Validate all internal links in documentation."""
    errors = []
    warnings = []
    
    for md_file in find_markdown_files(docs_dir):
        content = md_file.read_text(encoding='utf-8')
        links = extract_internal_links(content)
        
        for link in links:
            # Skip external links
            if link.startswith('http'):
                continue
            
            # Resolve relative path
            if link.startswith('../'):
                target = md_file.parent.parent / link[3:]
            elif link.startswith('./'):
                target = md_file.parent / link[2:]
            else:
                target = md_file.parent / link
            
            target = target.resolve()
            
            if not target.exists():
                errors.append(f"{md_file}: Broken link to {link}")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def extract_code_blocks(content: str) -> list[tuple[str, str]]:
    """Extract code blocks with language from markdown."""
    pattern = r'```(\w+)\n(.*?)```'
    matches = re.findall(pattern, content, re.DOTALL)
    return matches


def validate_python_syntax(code: str) -> bool:
    """Validate Python code syntax."""
    try:
        ast.parse(code)
        return True
    except SyntaxError:
        return False


def validate_code_examples(docs_dir: Path) -> ValidationResult:
    """Validate code examples in documentation."""
    errors = []
    warnings = []
    
    for md_file in find_markdown_files(docs_dir):
        content = md_file.read_text(encoding='utf-8')
        code_blocks = extract_code_blocks(content)
        
        for lang, code in code_blocks:
            if lang == 'python':
                # Skip incomplete examples (with ...)
                if '...' in code or '# ...' in code:
                    continue
                
                # Skip examples with placeholders
                if '{' in code and '}' in code:
                    continue
                
                if not validate_python_syntax(code):
                    errors.append(f"{md_file}: Invalid Python syntax in code block")
    
    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
    )


def get_public_modules(src_dir: Path) -> list[str]:
    """Get list of public Python modules."""
    modules = []
    
    for py_file in src_dir.rglob("*.py"):
        if py_file.name.startswith('_') and py_file.name != '__init__.py':
            continue
        
        # Convert path to module name
        relative = py_file.relative_to(src_dir.parent)
        module = str(relative).replace('/', '.').replace('\\', '.')[:-3]
        modules.append(module)
    
    return modules


def check_documentation_coverage(
    src_dir: Path,
    docs_dir: Path,
) -> ValidationResult:
    """Check if all modules have documentation."""
    errors = []
    warnings = []
    
    modules = get_public_modules(src_dir)
    documented = set()
    
    # Find documented modules in docs
    for md_file in find_markdown_files(docs_dir):
        content = md_file.read_text(encoding='utf-8')
        for module in modules:
            if module in content or module.split('.')[-1] in content:
                documented.add(module)
    
    # Check coverage
    undocumented = set(modules) - documented
    coverage = len(documented) / len(modules) * 100 if modules else 100
    
    if coverage < 50:
        warnings.append(f"Documentation coverage is {coverage:.1f}%")
    
    # Only report top-level undocumented modules
    for module in undocumented:
        if module.count('.') <= 2:  # Only report shallow modules
            warnings.append(f"Module {module} may not be documented")
    
    return ValidationResult(
        is_valid=True,  # Coverage is a warning, not error
        errors=errors,
        warnings=warnings,
    )


def main():
    """Run all validations."""
    docs_dir = Path("docs")
    src_dir = Path("src")
    
    if not docs_dir.exists():
        print("Error: docs/ directory not found")
        sys.exit(1)
    
    print("Validating documentation...")
    print()
    
    # Validate internal links
    print("Checking internal links...")
    link_result = validate_internal_links(docs_dir)
    for error in link_result.errors:
        print(f"  ERROR: {error}")
    for warning in link_result.warnings:
        print(f"  WARNING: {warning}")
    
    # Validate code examples
    print("Checking code examples...")
    code_result = validate_code_examples(docs_dir)
    for error in code_result.errors:
        print(f"  ERROR: {error}")
    for warning in code_result.warnings:
        print(f"  WARNING: {warning}")
    
    # Check coverage
    if src_dir.exists():
        print("Checking documentation coverage...")
        coverage_result = check_documentation_coverage(src_dir, docs_dir)
        for error in coverage_result.errors:
            print(f"  ERROR: {error}")
        for warning in coverage_result.warnings:
            print(f"  WARNING: {warning}")
    
    print()
    
    # Summary
    all_valid = link_result.is_valid and code_result.is_valid
    
    if all_valid:
        print("✅ Documentation validation passed")
        sys.exit(0)
    else:
        print("❌ Documentation validation failed")
        sys.exit(1)


if __name__ == "__main__":
    main()
