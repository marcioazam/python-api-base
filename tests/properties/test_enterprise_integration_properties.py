"""Property-based tests for integration and cross-cutting concerns.

**Feature: enterprise-features-2025, Tasks 10.2, 10.4**
**Validates: Requirements 10.2, 11.1**
"""

import ast
import re
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st
from pydantic import SecretStr


class TestPEP695Compliance:
    """**Feature: enterprise-features-2025, Property 21: PEP 695 Syntax Compliance**
    **Validates: Requirements 10.2**
    """

    def test_no_legacy_typevar_in_enterprise_modules(self) -> None:
        """Enterprise modules use PEP 695 syntax instead of legacy Generic[T]."""
        enterprise_modules = [
            "src/my_app/shared/webhook",
            "src/my_app/shared/file_upload",
            "src/my_app/shared/search",
            "src/my_app/shared/notification",
        ]

        legacy_patterns = [
            r"from typing import.*TypeVar",
            r"TypeVar\s*\(",
            r"Generic\s*\[",
        ]

        violations = []

        for module_path in enterprise_modules:
            path = Path(module_path)
            if not path.exists():
                continue

            for py_file in path.glob("**/*.py"):
                content = py_file.read_text()

                for pattern in legacy_patterns:
                    if re.search(pattern, content):
                        violations.append(f"{py_file}: {pattern}")

        assert len(violations) == 0, f"Legacy TypeVar/Generic found: {violations}"

    def test_generic_classes_use_pep695_syntax(self) -> None:
        """Generic classes use class Foo[T]: syntax."""
        # Check that our new modules use PEP 695
        files_to_check = [
            "src/my_app/shared/webhook/models.py",
            "src/my_app/shared/file_upload/models.py",
            "src/my_app/shared/search/models.py",
            "src/my_app/shared/notification/models.py",
        ]

        pep695_pattern = r"class\s+\w+\s*\[\s*\w+"

        for file_path in files_to_check:
            path = Path(file_path)
            if not path.exists():
                continue

            content = path.read_text()

            # Should have PEP 695 style generics
            if "Protocol" in content or "[T" in content:
                assert re.search(pep695_pattern, content), (
                    f"{file_path} should use PEP 695 syntax"
                )


class TestSecretStrNonDisclosure:
    """**Feature: enterprise-features-2025, Property 22: SecretStr Non-Disclosure**
    **Validates: Requirements 11.1**
    """

    # Use alphanumeric strings with min length to avoid false positives
    # (short strings like '*', ',', ':' can appear in repr output)
    secret_strategy = st.text(
        alphabet=st.characters(whitelist_categories=("Lu", "Ll", "Nd")),
        min_size=10,
        max_size=100,
    )

    @given(secret_value=secret_strategy)
    @settings(max_examples=100)
    def test_secretstr_str_hides_value(self, secret_value: str) -> None:
        """Converting SecretStr to string hides the actual value."""
        secret = SecretStr(secret_value)

        str_repr = str(secret)
        repr_repr = repr(secret)

        # Value should not appear in string representations
        assert secret_value not in str_repr
        assert secret_value not in repr_repr

        # Should show masked value
        assert "**" in str_repr or "SecretStr" in str_repr

    @given(secret_value=secret_strategy)
    @settings(max_examples=100)
    def test_secretstr_get_secret_value_reveals(self, secret_value: str) -> None:
        """get_secret_value() returns the actual secret."""
        secret = SecretStr(secret_value)

        revealed = secret.get_secret_value()
        assert revealed == secret_value

    @given(secret_value=secret_strategy)
    @settings(max_examples=50)
    def test_secretstr_not_in_dict_repr(self, secret_value: str) -> None:
        """SecretStr value not exposed when in dict."""
        secret = SecretStr(secret_value)
        data = {"secret": secret, "other": "visible"}

        dict_str = str(data)

        # Secret value should not appear
        assert secret_value not in dict_str

    @given(secret_value=secret_strategy)
    @settings(max_examples=50)
    def test_secretstr_not_in_format_string(self, secret_value: str) -> None:
        """SecretStr value not exposed in format strings."""
        secret = SecretStr(secret_value)

        formatted = f"Secret is: {secret}"

        assert secret_value not in formatted

    @given(
        secret1=st.text(min_size=1, max_size=50),
        secret2=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=50)
    def test_secretstr_equality_uses_value(
        self, secret1: str, secret2: str
    ) -> None:
        """SecretStr equality compares actual values."""
        s1 = SecretStr(secret1)
        s2 = SecretStr(secret2)

        if secret1 == secret2:
            assert s1 == s2
        else:
            assert s1 != s2


class TestNoHardcodedSecrets:
    """Tests for no hardcoded secrets in code."""

    def test_no_hardcoded_passwords_in_enterprise_modules(self) -> None:
        """No hardcoded passwords in enterprise modules."""
        enterprise_modules = [
            "src/my_app/shared/webhook",
            "src/my_app/shared/file_upload",
            "src/my_app/shared/search",
            "src/my_app/shared/notification",
        ]

        secret_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'token\s*=\s*["\'][^"\']+["\']',
        ]

        # Exclude test files and example values
        exclude_patterns = [
            r'test_',
            r'example',
            r'placeholder',
            r'SecretStr\(',
        ]

        violations = []

        for module_path in enterprise_modules:
            path = Path(module_path)
            if not path.exists():
                continue

            for py_file in path.glob("**/*.py"):
                if "test_" in py_file.name:
                    continue

                content = py_file.read_text()

                for pattern in secret_patterns:
                    matches = re.findall(pattern, content, re.IGNORECASE)
                    for match in matches:
                        # Check if it's an excluded pattern
                        is_excluded = any(
                            re.search(exc, match, re.IGNORECASE)
                            for exc in exclude_patterns
                        )
                        if not is_excluded:
                            violations.append(f"{py_file}: {match}")

        assert len(violations) == 0, f"Hardcoded secrets found: {violations}"


class TestResultPatternUsage:
    """Tests for Result pattern usage."""

    def test_enterprise_modules_use_result_pattern(self) -> None:
        """Enterprise modules use Result pattern for error handling."""
        files_with_result = [
            "src/my_app/shared/webhook/service.py",
            "src/my_app/shared/file_upload/service.py",
        ]

        for file_path in files_with_result:
            path = Path(file_path)
            if not path.exists():
                continue

            content = path.read_text()

            # Should import Result
            assert "Result" in content, f"{file_path} should use Result pattern"

            # Should use Ok/Err
            assert "Ok(" in content or "Err(" in content, (
                f"{file_path} should use Ok/Err"
            )
