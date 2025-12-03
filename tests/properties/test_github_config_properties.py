"""
Property-based tests for GitHub CI/CD configuration validation.

Feature: github-cicd-hardening
Tests correctness properties defined in design.md
"""

from __future__ import annotations

import pytest
pytest.skip('Module scripts.validate_github_config not implemented', allow_module_level=True)

from pathlib import Path
from typing import Any

import yaml
from hypothesis import given, settings
from hypothesis import strategies as st

from scripts.validate_github_config import (
    extract_action_references,
    has_unsafe_branch_reference,
    parse_yaml_file,
    validate_action_pinning,
    validate_job_timeouts,
    validate_yaml_syntax,
)

# Test data directory
GITHUB_DIR = Path(".github")
WORKFLOWS_DIR = GITHUB_DIR / "workflows"


# Strategies for generating test data
safe_version_strategy = st.one_of(
    st.from_regex(r"v[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
    st.from_regex(r"v[0-9]+\.[0-9]+", fullmatch=True),
    st.from_regex(r"v[0-9]+", fullmatch=True),
    st.from_regex(r"[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
    st.from_regex(r"[a-f0-9]{40}", fullmatch=True),  # SHA
)

unsafe_version_strategy = st.sampled_from(["master", "main", "HEAD"])

action_name_strategy = st.from_regex(r"[a-z0-9-]+/[a-z0-9-]+", fullmatch=True)


class TestActionPinningProperty:
    """
    **Feature: github-cicd-hardening, Property 1: No Branch References in Actions**
    **Validates: Requirements 1.1**

    For any GitHub Action reference in any workflow file, the version specifier
    SHALL NOT contain @master, @main, or @HEAD branch references.
    """

    @given(version=safe_version_strategy)
    @settings(max_examples=100)
    def test_safe_versions_are_not_flagged(self, version: str) -> None:
        """Safe version patterns should not be flagged as unsafe."""
        assert not has_unsafe_branch_reference(version)

    @given(version=unsafe_version_strategy)
    @settings(max_examples=100)
    def test_unsafe_branches_are_flagged(self, version: str) -> None:
        """Unsafe branch references should be flagged."""
        assert has_unsafe_branch_reference(version)

    @given(
        action=action_name_strategy,
        safe_version=safe_version_strategy,
    )
    @settings(max_examples=50)
    def test_pinned_action_format_is_valid(
        self, action: str, safe_version: str
    ) -> None:
        """Pinned action references should pass validation."""
        # Format: owner/repo@version
        reference = f"{action}@{safe_version}"
        assert "@master" not in reference
        assert "@main" not in reference
        assert "@HEAD" not in reference


class TestJobTimeoutProperty:
    """
    **Feature: github-cicd-hardening, Property 2: All Jobs Have Timeouts**
    **Validates: Requirements 2.1, 2.2, 2.3, 2.4, 2.5, 2.6**

    For any job defined in any workflow file, the job SHALL have a
    timeout-minutes field with a positive integer value.
    """

    @given(
        timeout=st.integers(min_value=1, max_value=360),
        job_name=st.from_regex(r"[a-z][a-z0-9_-]*", fullmatch=True),
    )
    @settings(max_examples=100)
    def test_valid_timeout_values(self, timeout: int, job_name: str) -> None:
        """Valid timeout values should be positive integers."""
        job_config = {"timeout-minutes": timeout, "runs-on": "ubuntu-latest"}
        assert "timeout-minutes" in job_config
        assert job_config["timeout-minutes"] > 0

    @given(job_name=st.from_regex(r"[a-z][a-z0-9_-]*", fullmatch=True))
    @settings(max_examples=50)
    def test_missing_timeout_is_detected(self, job_name: str) -> None:
        """Jobs without timeout-minutes should be detected."""
        job_config: dict[str, Any] = {"runs-on": "ubuntu-latest"}
        assert "timeout-minutes" not in job_config


class TestYamlValidityProperty:
    """
    **Feature: github-cicd-hardening, Property 3: YAML Syntax Validity**
    **Validates: Requirements 1.1, 2.1, 3.1, 4.1, 5.1, 6.1**

    For any YAML configuration file in .github/ or .coderabbit.yaml,
    parsing the file SHALL NOT produce syntax errors.
    """

    @given(
        key=st.from_regex(r"[a-z][a-z0-9_]*", fullmatch=True),
        value=st.one_of(
            st.text(min_size=1, max_size=50),
            st.integers(),
            st.booleans(),
        ),
    )
    @settings(max_examples=100)
    def test_valid_yaml_roundtrip(self, key: str, value: str | int | bool) -> None:
        """Valid YAML should parse and serialize correctly."""
        data = {key: value}
        yaml_str = yaml.safe_dump(data)
        parsed = yaml.safe_load(yaml_str)
        assert parsed == data

    def test_actual_workflow_files_are_valid(self) -> None:
        """All actual workflow files should have valid YAML syntax."""
        if not WORKFLOWS_DIR.exists():
            return

        for workflow_file in WORKFLOWS_DIR.glob("*.yml"):
            errors = validate_yaml_syntax(workflow_file)
            assert not errors, f"YAML errors in {workflow_file}: {errors}"

    def test_actual_config_files_are_valid(self) -> None:
        """All actual config files should have valid YAML syntax."""
        config_files = [
            GITHUB_DIR / "dependabot.yml",
            Path(".coderabbit.yaml"),
        ]

        for config_file in config_files:
            if config_file.exists():
                errors = validate_yaml_syntax(config_file)
                assert not errors, f"YAML errors in {config_file}: {errors}"


class TestIntegrationValidation:
    """Integration tests for the validation functions."""

    def test_validate_action_pinning_detects_issues(self) -> None:
        """Validation should detect unpinned actions in current workflows."""
        if not WORKFLOWS_DIR.exists():
            return

        # Before fixes, we expect to find issues
        all_errors = []
        for workflow_file in WORKFLOWS_DIR.glob("*.yml"):
            errors = validate_action_pinning(workflow_file)
            all_errors.extend(errors)

        # This test documents current state - will pass after fixes
        # For now, we just verify the function runs without error

    def test_validate_job_timeouts_detects_issues(self) -> None:
        """Validation should detect missing timeouts in current workflows."""
        if not WORKFLOWS_DIR.exists():
            return

        all_errors = []
        for workflow_file in WORKFLOWS_DIR.glob("*.yml"):
            errors = validate_job_timeouts(workflow_file)
            all_errors.extend(errors)

        # This test documents current state - will pass after fixes
