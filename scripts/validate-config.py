#!/usr/bin/env python
"""
Script de Validação de Configurações
=====================================

Valida todos os arquivos de configuração do projeto para garantir
que estão corretos e completos antes de deployments ou onboarding.

Usage:
    python scripts/validate-config.py
    python scripts/validate-config.py --strict  # Fail on warnings
    python scripts/validate-config.py --fix     # Auto-fix when possible

Exit Codes:
    0 - All validations passed
    1 - Validation errors found
    2 - Critical errors (missing required files)
"""

import json
import sys
import tomllib
from configparser import ConfigParser
from pathlib import Path
from typing import Any

try:
    import typer
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("ERROR: Required dependencies not installed")
    print("Run: uv sync --dev")
    sys.exit(2)

app = typer.Typer(help="Validate project configuration files")
console = Console()

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Required files
REQUIRED_FILES = {
    ".env.example": "Environment variables template",
    ".gitignore": "Git ignore patterns",
    ".pre-commit-config.yaml": "Pre-commit hooks configuration",
    ".secrets.baseline": "Detect-secrets baseline",
    "alembic.ini": "Alembic database migrations configuration",
    "pyproject.toml": "Python project configuration",
    "ruff.toml": "Ruff linter/formatter configuration",
    "Makefile": "Build automation",
    "docs/environment-variables.md": "Environment variables documentation",
}

# Required env vars (obrigatórios em .env)
REQUIRED_ENV_VARS = [
    "APP_NAME",
    "APP_ENV",
    "DATABASE__URL",
    "SECURITY__SECRET_KEY",
    "REDIS__URL",
]

# Validation results
class ValidationResult:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.info: list[str] = []
        self.files_checked: int = 0
        self.validations_run: int = 0

    def add_error(self, msg: str) -> None:
        self.errors.append(f"[ERROR] {msg}")

    def add_warning(self, msg: str) -> None:
        self.warnings.append(f"[WARNING] {msg}")

    def add_info(self, msg: str) -> None:
        self.info.append(f"[INFO] {msg}")

    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def has_warnings(self) -> bool:
        return len(self.warnings) > 0


def read_file_safe(file_path: Path) -> str | None:
    """Read file content safely."""
    try:
        return file_path.read_text(encoding="utf-8")
    except Exception as e:
        console.print(f"[red]Error reading {file_path}: {e}[/red]")
        return None


def validate_required_files(result: ValidationResult) -> None:
    """Validate that all required files exist."""
    console.print("\n[bold blue]Validating Required Files[/bold blue]")

    for file_path, description in REQUIRED_FILES.items():
        full_path = PROJECT_ROOT / file_path
        result.validations_run += 1

        if not full_path.exists():
            result.add_error(f"{file_path} not found ({description})")
        else:
            result.files_checked += 1
            console.print(f"  [OK] {file_path}")


def validate_env_example(result: ValidationResult) -> None:
    """Validate .env.example structure and required variables."""
    console.print("\n[bold blue] Validating .env.example[/bold blue]")

    env_example_path = PROJECT_ROOT / ".env.example"
    if not env_example_path.exists():
        return

    result.validations_run += 1
    content = read_file_safe(env_example_path)
    if not content:
        result.add_error(".env.example is empty or unreadable")
        return

    # Parse variables
    env_vars = {}
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=")[0].strip()
            env_vars[key] = line

    # Check required variables
    missing_required = []
    for var in REQUIRED_ENV_VARS:
        if var not in env_vars:
            missing_required.append(var)

    if missing_required:
        result.add_error(
            f".env.example missing required variables: {', '.join(missing_required)}"
        )
    else:
        console.print(f"  [OK] All {len(REQUIRED_ENV_VARS)} required variables present")

    # Check for placeholder values
    placeholder_issues = []
    for key, line in env_vars.items():
        if key in REQUIRED_ENV_VARS:
            value = line.split("=", 1)[1] if "=" in line else ""
            if not value or value in ["", '""', "''", "changeme", "CHANGE_ME"]:
                if key != "SENTRY__DSN":  # Optional
                    placeholder_issues.append(key)

    if placeholder_issues:
        result.add_warning(
            f"Variables with placeholder values: {', '.join(placeholder_issues)}"
        )

    result.add_info(f"Total variables in .env.example: {len(env_vars)}")


def fix_env_file(result: ValidationResult) -> bool:
    """Auto-fix .env file by creating from .env.example."""
    import secrets

    env_path = PROJECT_ROOT / ".env"
    env_example_path = PROJECT_ROOT / ".env.example"

    fixed = False

    # Create .env if it doesn't exist
    if not env_path.exists() and env_example_path.exists():
        try:
            content = env_example_path.read_text(encoding="utf-8")
            env_path.write_text(content, encoding="utf-8")
            console.print("[green]  [FIX] Created .env from .env.example[/green]")
            fixed = True
        except Exception as e:
            result.add_warning(f"Could not create .env: {e}")
            return False

    # Fix weak SECURITY__SECRET_KEY
    if env_path.exists():
        try:
            content = env_path.read_text(encoding="utf-8")
            lines = content.splitlines()
            modified = False

            for i, line in enumerate(lines):
                if line.strip().startswith("SECURITY__SECRET_KEY="):
                    value = line.split("=", 1)[1].strip().strip('"\'')
                    weak_values = [
                        "changeme",
                        "CHANGE_ME",
                        "your-secret-key-here",
                        "your-super-secret-key-change-in-production-min-32-chars",
                    ]

                    if value in weak_values or len(value) < 32:
                        new_key = secrets.token_urlsafe(64)
                        lines[i] = f'SECURITY__SECRET_KEY="{new_key}"'
                        modified = True
                        console.print(
                            "[green]  [FIX] Generated new SECURITY__SECRET_KEY[/green]"
                        )
                        break

            if modified:
                env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
                fixed = True

        except Exception as e:
            result.add_warning(f"Could not fix SECRET_KEY: {e}")

    return fixed


def validate_env_file(result: ValidationResult) -> None:
    """Validate .env file if it exists."""
    console.print("\n[bold blue] Validating .env[/bold blue]")

    env_path = PROJECT_ROOT / ".env"
    result.validations_run += 1

    if not env_path.exists():
        result.add_warning(".env file not found (create from .env.example)")
        return

    content = read_file_safe(env_path)
    if not content:
        result.add_error(".env is empty")
        return

    # Parse variables
    env_vars = {}
    for line in content.splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key = line.split("=")[0].strip()
            value = line.split("=", 1)[1].strip() if "=" in line else ""
            env_vars[key] = value

    # Check required variables
    missing = []
    empty = []
    for var in REQUIRED_ENV_VARS:
        if var not in env_vars:
            missing.append(var)
        elif not env_vars[var] or env_vars[var] in ['""', "''", "changeme"]:
            empty.append(var)

    if missing:
        result.add_error(f".env missing required variables: {', '.join(missing)}")

    if empty:
        result.add_warning(f".env has empty required variables: {', '.join(empty)}")

    if not missing and not empty:
        console.print(f"  [OK] All {len(REQUIRED_ENV_VARS)} required variables configured")

    # Security check: SECURITY__SECRET_KEY length
    if "SECURITY__SECRET_KEY" in env_vars:
        secret_key = env_vars["SECURITY__SECRET_KEY"].strip('"\'')
        if len(secret_key) < 32:
            result.add_error(
                f"SECURITY__SECRET_KEY too short ({len(secret_key)} chars, min 32)"
            )
        elif secret_key in ["changeme", "CHANGE_ME", "your-secret-key-here"]:
            result.add_error("SECURITY__SECRET_KEY is placeholder, generate real key")
        else:
            console.print("  [OK] SECURITY__SECRET_KEY length valid")


def validate_pyproject_toml(result: ValidationResult) -> None:
    """Validate pyproject.toml syntax and required sections."""
    console.print("\n[bold blue] Validating pyproject.toml[/bold blue]")

    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        return

    result.validations_run += 1

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        # Check required sections
        required_sections = ["project", "build-system", "tool.pytest.ini_options"]
        missing_sections = []

        for section in required_sections:
            parts = section.split(".")
            current = data
            for part in parts:
                if part not in current:
                    missing_sections.append(section)
                    break
                current = current[part]

        if missing_sections:
            result.add_error(
                f"pyproject.toml missing sections: {', '.join(missing_sections)}"
            )
        else:
            console.print("  [OK] All required sections present")

        # Check tool configurations
        tool_configs = [
            "ruff",
            "mypy",
            "pytest",
            "coverage",
            "bandit",
            "commitizen",
            "hypothesis",
        ]
        configured_tools = []
        for tool in tool_configs:
            if f"tool.{tool}" in str(data) or tool in data.get("tool", {}):
                configured_tools.append(tool)

        result.add_info(f"Configured tools: {', '.join(configured_tools)}")
        console.print(f"  [OK] {len(configured_tools)} tool configurations found")

    except tomllib.TOMLDecodeError as e:
        result.add_error(f"pyproject.toml syntax error: {e}")
    except Exception as e:
        result.add_error(f"pyproject.toml validation failed: {e}")


def validate_ruff_toml(result: ValidationResult) -> None:
    """Validate ruff.toml syntax and configuration."""
    console.print("\n[bold blue] Validating ruff.toml[/bold blue]")

    ruff_path = PROJECT_ROOT / "ruff.toml"
    if not ruff_path.exists():
        return

    result.validations_run += 1

    try:
        with open(ruff_path, "rb") as f:
            data = tomllib.load(f)

        # Check critical settings
        if "line-length" not in data:
            result.add_warning("ruff.toml: line-length not configured")
        else:
            console.print(f"  [OK] line-length: {data['line-length']}")

        if "lint" in data and "select" in data["lint"]:
            rules = data["lint"]["select"]
            console.print(f"  [OK] {len(rules)} rule categories enabled")
        else:
            result.add_warning("ruff.toml: lint.select not configured")

        # Check if preview features enabled
        if "format" in data and data["format"].get("preview"):
            result.add_info("Preview features enabled in formatter")

    except tomllib.TOMLDecodeError as e:
        result.add_error(f"ruff.toml syntax error: {e}")
    except Exception as e:
        result.add_error(f"ruff.toml validation failed: {e}")


def validate_alembic_ini(result: ValidationResult) -> None:
    """Validate alembic.ini syntax and configuration."""
    console.print("\n[bold blue]  Validating alembic.ini[/bold blue]")

    alembic_path = PROJECT_ROOT / "alembic.ini"
    if not alembic_path.exists():
        return

    result.validations_run += 1

    try:
        config = ConfigParser()
        config.read(alembic_path)

        # Check required sections
        required_sections = ["alembic", "loggers", "handlers", "formatters"]
        missing = [s for s in required_sections if s not in config.sections()]

        if missing:
            result.add_error(f"alembic.ini missing sections: {', '.join(missing)}")
        else:
            console.print("  [OK] All required sections present")

        # Check script_location
        if "alembic" in config.sections():
            script_location = config.get("alembic", "script_location", fallback=None)
            if not script_location:
                result.add_error("alembic.ini: script_location not configured")
            elif not (PROJECT_ROOT / script_location).exists():
                result.add_error(
                    f"alembic.ini: script_location '{script_location}' not found"
                )
            else:
                console.print(f"  [OK] script_location: {script_location}")

    except Exception as e:
        result.add_error(f"alembic.ini validation failed: {e}")


def validate_secrets_baseline(result: ValidationResult) -> None:
    """Validate .secrets.baseline JSON structure."""
    console.print("\n[bold blue] Validating .secrets.baseline[/bold blue]")

    baseline_path = PROJECT_ROOT / ".secrets.baseline"
    if not baseline_path.exists():
        return

    result.validations_run += 1

    try:
        with open(baseline_path) as f:
            data = json.load(f)

        # Check required keys
        required_keys = ["version", "plugins_used", "filters_used", "results"]
        missing = [k for k in required_keys if k not in data]

        if missing:
            result.add_error(
                f".secrets.baseline missing keys: {', '.join(missing)}"
            )
        else:
            console.print("  [OK] All required keys present")

        # Check plugins
        if "plugins_used" in data:
            plugins = [p.get("name", "unknown") for p in data["plugins_used"]]
            console.print(f"  [OK] {len(plugins)} plugins configured")

            # Check for critical plugins
            critical_plugins = [
                "AWSKeyDetector",
                "PrivateKeyDetector",
                "JwtTokenDetector",
            ]
            missing_critical = [p for p in critical_plugins if p not in plugins]
            if missing_critical:
                result.add_warning(
                    f"Missing critical plugins: {', '.join(missing_critical)}"
                )

        # Check results
        if "results" in data:
            total_secrets = sum(len(secrets) for secrets in data["results"].values())
            if total_secrets > 0:
                result.add_info(
                    f"{total_secrets} known false positives in baseline"
                )

    except json.JSONDecodeError as e:
        result.add_error(f".secrets.baseline syntax error: {e}")
    except Exception as e:
        result.add_error(f".secrets.baseline validation failed: {e}")


def validate_gitignore(result: ValidationResult) -> None:
    """Validate .gitignore has critical patterns."""
    console.print("\n[bold blue] Validating .gitignore[/bold blue]")

    gitignore_path = PROJECT_ROOT / ".gitignore"
    if not gitignore_path.exists():
        return

    result.validations_run += 1
    content = read_file_safe(gitignore_path)
    if not content:
        return

    # Critical patterns that MUST be present
    critical_patterns = [
        ".env",
        "__pycache__",
        "*.pyc",  # Can be covered by *.py[cod]
        ".venv",
        ".secrets",
        "*.key",
        "*.pem",
    ]

    lines = [line.strip() for line in content.splitlines() if line.strip()]
    missing_critical = []

    for pattern in critical_patterns:
        # Check if pattern exists (with or without leading **)
        # Also check for equivalent patterns (e.g., *.py[cod] covers *.pyc)
        found = any(
            pattern in line or f"**/{pattern}" in line or f"*{pattern}" in line
            for line in lines
        )

        # Special case: *.pyc is covered by *.py[cod]
        if not found and pattern == "*.pyc":
            found = any("*.py[cod]" in line or "**/*.py[cod]" in line for line in lines)

        if not found:
            missing_critical.append(pattern)

    if missing_critical:
        result.add_error(
            f".gitignore missing critical patterns: {', '.join(missing_critical)}"
        )
    else:
        console.print(f"  [OK] All {len(critical_patterns)} critical patterns present")

    result.add_info(f"Total patterns in .gitignore: {len(lines)}")


def validate_precommit_config(result: ValidationResult) -> None:
    """Validate .pre-commit-config.yaml has critical hooks."""
    console.print("\n[bold blue] Validating .pre-commit-config.yaml[/bold blue]")

    precommit_path = PROJECT_ROOT / ".pre-commit-config.yaml"
    if not precommit_path.exists():
        return

    result.validations_run += 1
    content = read_file_safe(precommit_path)
    if not content:
        return

    # Critical hooks
    critical_hooks = [
        "ruff",
        "ruff-format",
        "detect-secrets",
        "check-yaml",
        "end-of-file-fixer",
    ]

    missing_critical = []
    for hook in critical_hooks:
        if f"id: {hook}" not in content:
            missing_critical.append(hook)

    if missing_critical:
        result.add_error(
            f".pre-commit-config.yaml missing critical hooks: {', '.join(missing_critical)}"
        )
    else:
        console.print(f"  [OK] All {len(critical_hooks)} critical hooks configured")

    # Count total hooks
    total_hooks = content.count("- id:")
    result.add_info(f"Total pre-commit hooks configured: {total_hooks}")


def validate_makefile(result: ValidationResult) -> None:
    """Validate Makefile has critical targets."""
    console.print("\n[bold blue] Validating Makefile[/bold blue]")

    makefile_path = PROJECT_ROOT / "Makefile"
    if not makefile_path.exists():
        return

    result.validations_run += 1
    content = read_file_safe(makefile_path)
    if not content:
        return

    # Critical targets
    critical_targets = [
        "help",
        "setup",
        "install",
        "test",
        "lint",
        "format",
        "clean",
        "migrate",
    ]

    missing_critical = []
    for target in critical_targets:
        if f"{target}:" not in content:
            missing_critical.append(target)

    if missing_critical:
        result.add_error(
            f"Makefile missing critical targets: {', '.join(missing_critical)}"
        )
    else:
        console.print(f"  [OK] All {len(critical_targets)} critical targets present")

    # Count total targets
    total_targets = content.count(":\n\t") + content.count(": ##")
    result.add_info(f"Total Makefile targets: {total_targets}")


def validate_env_vars_documentation(result: ValidationResult) -> None:
    """Validate environment variables documentation is complete."""
    console.print("\n[bold blue] Validating Environment Variables Documentation[/bold blue]")

    docs_path = PROJECT_ROOT / "docs" / "environment-variables.md"
    if not docs_path.exists():
        return

    result.validations_run += 1
    content = read_file_safe(docs_path)
    if not content:
        return

    # Check that all required vars are documented
    missing_docs = []
    for var in REQUIRED_ENV_VARS:
        if f"### {var}" not in content and f"## {var}" not in content:
            missing_docs.append(var)

    if missing_docs:
        result.add_warning(
            f"Required variables not documented: {', '.join(missing_docs)}"
        )
    else:
        console.print(
            f"  [OK] All {len(REQUIRED_ENV_VARS)} required variables documented"
        )

    # Count total documented variables
    total_vars = content.count("### ") + content.count("## ") - content.count("## ")
    result.add_info(f"Total documented variables: {total_vars}")


def validate_docker_compose(result: ValidationResult) -> None:
    """Validate Docker Compose files exist and have critical services."""
    console.print("\n[bold blue]Validating Docker Compose[/bold blue]")

    docker_files = [
        "deployments/docker/docker-compose.base.yml",
        "deployments/docker/docker-compose.dev.yml",
        "deployments/docker/docker-compose.production.yml",
    ]

    result.validations_run += 1

    for file_path in docker_files:
        full_path = PROJECT_ROOT / file_path
        if not full_path.exists():
            result.add_warning(f"Docker Compose file not found: {file_path}")
        else:
            console.print(f"  [OK] {file_path}")


def validate_readme(result: ValidationResult) -> None:
    """Validate README.md has essential sections."""
    console.print("\n[bold blue]Validating README.md[/bold blue]")

    readme_path = PROJECT_ROOT / "README.md"
    if not readme_path.exists():
        result.add_error("README.md not found")
        return

    result.validations_run += 1
    content = read_file_safe(readme_path)
    if not content:
        return

    # Essential sections
    essential_sections = [
        "## Features",
        "## Quick Start",
        "## Installation",
        "## Usage",
        "## Documentation",
    ]

    missing_sections = []
    for section in essential_sections:
        if section not in content:
            missing_sections.append(section.replace("## ", ""))

    if missing_sections:
        result.add_warning(
            f"README.md missing recommended sections: {', '.join(missing_sections)}"
        )
    else:
        console.print(
            f"  [OK] All {len(essential_sections)} essential sections present"
        )


def fix_license(result: ValidationResult) -> bool:
    """Auto-fix LICENSE by creating MIT license template."""
    license_path = PROJECT_ROOT / "LICENSE"

    if not license_path.exists():
        try:
            from datetime import datetime

            mit_license = f"""MIT License

Copyright (c) {datetime.now().year} API Team

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
            license_path.write_text(mit_license, encoding="utf-8")
            console.print("[green]  [FIX] Created LICENSE file (MIT)[/green]")
            return True
        except Exception as e:
            result.add_warning(f"Could not create LICENSE: {e}")
            return False

    return False


def validate_license(result: ValidationResult) -> None:
    """Validate LICENSE file exists."""
    console.print("\n[bold blue]Validating LICENSE[/bold blue]")

    license_path = PROJECT_ROOT / "LICENSE"
    result.validations_run += 1

    if not license_path.exists():
        result.add_warning("LICENSE file not found")
    else:
        console.print("  [OK] LICENSE file exists")


def validate_dependencies(result: ValidationResult) -> None:
    """Validate pyproject.toml dependencies have versions pinned."""
    console.print("\n[bold blue]Validating Dependencies[/bold blue]")

    pyproject_path = PROJECT_ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        return

    result.validations_run += 1

    try:
        with open(pyproject_path, "rb") as f:
            data = tomllib.load(f)

        if "project" not in data or "dependencies" not in data["project"]:
            result.add_warning("pyproject.toml: no dependencies section found")
            return

        deps = data["project"]["dependencies"]
        unpinned = []

        for dep in deps:
            # Check if dependency has version constraint
            if ">=" not in dep and "==" not in dep and "~=" not in dep and "<" not in dep:
                # Extract package name
                pkg_name = dep.split("[")[0].strip()
                unpinned.append(pkg_name)

        if unpinned:
            result.add_warning(
                f"Dependencies without version constraints: {', '.join(unpinned[:5])}"
                + (f" and {len(unpinned) - 5} more" if len(unpinned) > 5 else "")
            )
        else:
            console.print(f"  [OK] All {len(deps)} dependencies have version constraints")

    except Exception as e:
        result.add_warning(f"Could not validate dependencies: {e}")


def validate_github_workflows(result: ValidationResult) -> None:
    """Validate GitHub workflows syntax."""
    console.print("\n[bold blue]Validating GitHub Workflows[/bold blue]")

    workflows_dir = PROJECT_ROOT / ".github" / "workflows"
    if not workflows_dir.exists():
        result.add_warning(".github/workflows directory not found")
        return

    result.validations_run += 1
    workflow_files = list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))

    if not workflow_files:
        result.add_warning("No workflow files found in .github/workflows")
        return

    try:
        import yaml

        valid_workflows = 0
        for workflow_file in workflow_files:
            try:
                with open(workflow_file) as f:
                    data = yaml.safe_load(f)

                # Check for required keys
                if "name" not in data:
                    result.add_warning(f"{workflow_file.name}: missing 'name' key")
                elif "on" not in data and "true" not in data:
                    result.add_warning(f"{workflow_file.name}: missing 'on' trigger")
                elif "jobs" not in data:
                    result.add_warning(f"{workflow_file.name}: missing 'jobs' section")
                else:
                    valid_workflows += 1

            except yaml.YAMLError as e:
                result.add_error(f"{workflow_file.name}: YAML syntax error - {e}")
            except Exception as e:
                result.add_warning(f"{workflow_file.name}: validation error - {e}")

        if valid_workflows > 0:
            console.print(
                f"  [OK] {valid_workflows}/{len(workflow_files)} workflows valid"
            )

    except ImportError:
        result.add_info(
            "PyYAML not installed, skipping workflow validation (install: pip install pyyaml)"
        )


def print_summary(result: ValidationResult, strict: bool) -> None:
    """Print validation summary."""
    console.print("\n" + "=" * 70)
    console.print("[bold] Validation Summary[/bold]")
    console.print("=" * 70)

    # Statistics
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")

    table.add_row("Files Checked", str(result.files_checked))
    table.add_row("Validations Run", str(result.validations_run))
    table.add_row("Errors", str(len(result.errors)))
    table.add_row("Warnings", str(len(result.warnings)))
    table.add_row("Info", str(len(result.info)))

    console.print(table)

    # Errors
    if result.errors:
        console.print("\n[bold red][FAIL] Errors:[/bold red]")
        for error in result.errors:
            console.print(f"  {error}")

    # Warnings
    if result.warnings:
        console.print("\n[bold yellow][WARN]  Warnings:[/bold yellow]")
        for warning in result.warnings:
            console.print(f"  {warning}")

    # Info
    if result.info:
        console.print("\n[bold blue][INFO]  Information:[/bold blue]")
        for info in result.info:
            console.print(f"  {info}")

    # Final status
    console.print("\n" + "=" * 70)
    if result.has_errors():
        console.print("[bold red][FAIL] Validation FAILED[/bold red]")
    elif strict and result.has_warnings():
        console.print("[bold yellow][WARN]  Validation FAILED (strict mode)[/bold yellow]")
    else:
        console.print("[bold green][OK] Validation PASSED[/bold green]")
    console.print("=" * 70 + "\n")


@app.command()
def main(
    strict: bool = typer.Option(
        False, "--strict", help="Fail on warnings (treat warnings as errors)"
    ),
    fix: bool = typer.Option(
        False, "--fix", help="Auto-fix issues when possible (.env, LICENSE, SECRET_KEY)"
    ),
) -> None:
    """Validate all project configuration files."""
    console.print("[bold green] Configuration Validation Started[/bold green]\n")

    if fix:
        console.print("[bold yellow]Auto-fix mode enabled[/bold yellow]\n")

    result = ValidationResult()

    # Run fixes if enabled
    if fix:
        console.print("[bold blue]Running auto-fixes...[/bold blue]")
        fix_env_file(result)
        fix_license(result)
        console.print()

    # Run all validations
    validate_required_files(result)
    validate_env_example(result)
    validate_env_file(result)
    validate_pyproject_toml(result)
    validate_ruff_toml(result)
    validate_alembic_ini(result)
    validate_secrets_baseline(result)
    validate_gitignore(result)
    validate_precommit_config(result)
    validate_makefile(result)
    validate_env_vars_documentation(result)

    # Additional validations
    validate_docker_compose(result)
    validate_readme(result)
    validate_license(result)
    validate_dependencies(result)
    validate_github_workflows(result)

    # Print summary
    print_summary(result, strict)

    # Exit with appropriate code
    if result.has_errors():
        sys.exit(1)
    elif strict and result.has_warnings():
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    app()
