"""
GitHub CI/CD Configuration Validator.

Validates GitHub Actions workflows, Dependabot, and CodeRabbit configurations
for security best practices including action pinning and timeout configuration.

Requirements: 1.1, 2.1
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    from collections.abc import Iterator

# Patterns for detecting unsafe action references
UNSAFE_BRANCH_PATTERNS = frozenset({"@master", "@main", "@HEAD"})
ACTION_REFERENCE_PATTERN = re.compile(r"uses:\s*([^@\s]+)@(\S+)")


@dataclass(frozen=True)
class ValidationError:
    """Represents a validation error found in configuration."""

    file: str
    line: int | None
    message: str
    severity: str  # critical, high, medium, low


@dataclass(frozen=True)
class ActionReference:
    """Represents a GitHub Action reference."""

    action: str
    version: str
    line: int


def parse_yaml_file(file_path: Path) -> dict | None:
    """Parse a YAML file and return its contents."""
    try:
        with file_path.open(encoding="utf-8") as f:
            return yaml.safe_load(f)
    except yaml.YAMLError:
        return None


def extract_action_references(file_path: Path) -> Iterator[ActionReference]:
    """Extract all action references from a workflow file."""
    try:
        with file_path.open(encoding="utf-8") as f:
            for line_num, line in enumerate(f, start=1):
                match = ACTION_REFERENCE_PATTERN.search(line)
                if match:
                    yield ActionReference(
                        action=match.group(1),
                        version=match.group(2),
                        line=line_num,
                    )
    except OSError:
        return


def has_unsafe_branch_reference(version: str) -> bool:
    """Check if a version string contains an unsafe branch reference."""
    return any(pattern in f"@{version}" for pattern in UNSAFE_BRANCH_PATTERNS)


def validate_action_pinning(file_path: Path) -> list[ValidationError]:
    """Validate that all actions use pinned versions, not branch references."""
    errors: list[ValidationError] = []

    for ref in extract_action_references(file_path):
        if has_unsafe_branch_reference(ref.version):
            errors.append(
                ValidationError(
                    file=str(file_path),
                    line=ref.line,
                    message=f"Action '{ref.action}' uses unsafe branch reference '@{ref.version}'. "
                    f"Use a specific version tag or SHA instead.",
                    severity="high",
                )
            )

    return errors


def validate_job_timeouts(file_path: Path) -> list[ValidationError]:
    """Validate that all jobs have timeout-minutes configured."""
    errors: list[ValidationError] = []
    content = parse_yaml_file(file_path)

    if content is None:
        errors.append(
            ValidationError(
                file=str(file_path),
                line=None,
                message="Failed to parse YAML file",
                severity="critical",
            )
        )
        return errors

    jobs = content.get("jobs", {})
    if not isinstance(jobs, dict):
        return errors

    for job_name, job_config in jobs.items():
        if not isinstance(job_config, dict):
            continue

        if "timeout-minutes" not in job_config:
            errors.append(
                ValidationError(
                    file=str(file_path),
                    line=None,
                    message=f"Job '{job_name}' does not have 'timeout-minutes' configured",
                    severity="medium",
                )
            )

    return errors


def validate_yaml_syntax(file_path: Path) -> list[ValidationError]:
    """Validate YAML file syntax."""
    errors: list[ValidationError] = []

    try:
        with file_path.open(encoding="utf-8") as f:
            yaml.safe_load(f)
    except yaml.YAMLError as e:
        errors.append(
            ValidationError(
                file=str(file_path),
                line=getattr(e, "problem_mark", None) and e.problem_mark.line,
                message=f"YAML syntax error: {e}",
                severity="critical",
            )
        )

    return errors


def get_workflow_files(github_dir: Path) -> list[Path]:
    """Get all workflow YAML files from .github/workflows directory."""
    workflows_dir = github_dir / "workflows"
    if not workflows_dir.exists():
        return []
    return list(workflows_dir.glob("*.yml")) + list(workflows_dir.glob("*.yaml"))


def get_config_files(root_dir: Path) -> list[Path]:
    """Get all GitHub and related config files."""
    files: list[Path] = []
    github_dir = root_dir / ".github"

    if github_dir.exists():
        files.extend(get_workflow_files(github_dir))
        dependabot = github_dir / "dependabot.yml"
        if dependabot.exists():
            files.append(dependabot)

    coderabbit = root_dir / ".coderabbit.yaml"
    if coderabbit.exists():
        files.append(coderabbit)

    return files


def validate_all(root_dir: Path) -> list[ValidationError]:
    """Run all validations on GitHub configuration files."""
    all_errors: list[ValidationError] = []
    github_dir = root_dir / ".github"

    # Validate workflow files
    for workflow_file in get_workflow_files(github_dir):
        all_errors.extend(validate_yaml_syntax(workflow_file))
        all_errors.extend(validate_action_pinning(workflow_file))
        all_errors.extend(validate_job_timeouts(workflow_file))

    # Validate other config files
    for config_file in [github_dir / "dependabot.yml", root_dir / ".coderabbit.yaml"]:
        if config_file.exists():
            all_errors.extend(validate_yaml_syntax(config_file))

    return all_errors


def format_error(error: ValidationError) -> str:
    """Format a validation error for display."""
    location = f"{error.file}"
    if error.line:
        location += f":{error.line}"
    return f"[{error.severity.upper()}] {location}: {error.message}"


def main() -> int:
    """Main entry point for the validation script."""
    root_dir = Path.cwd()
    errors = validate_all(root_dir)

    if not errors:
        print("✅ All GitHub configurations are valid!")
        return 0

    print(f"❌ Found {len(errors)} validation error(s):\n")

    # Sort by severity
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    sorted_errors = sorted(errors, key=lambda e: severity_order.get(e.severity, 4))

    for error in sorted_errors:
        print(format_error(error))

    # Return non-zero if any critical or high severity errors
    has_blocking = any(e.severity in ("critical", "high") for e in errors)
    return 1 if has_blocking else 0


if __name__ == "__main__":
    sys.exit(main())
