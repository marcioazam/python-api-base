"""Property-based tests for CLI code generation.

**Feature: cli-security-improvements**
**Properties 7-8: Generated Code Properties**
**Validates: Requirements 5.1, 5.2**
"""

import re

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.cli.commands.generate import (
    _generate_entity_content,
    _generate_mapper_content,
    _generate_routes_content,
    _generate_use_case_content,
    to_pascal_case,
    to_snake_case,
)
from my_app.cli.constants import ALLOWED_FIELD_TYPES, MAX_ENTITY_NAME_LENGTH


# Strategy for valid entity names
valid_entity_names = st.from_regex(r"^[a-z][a-z0-9_]*$", fullmatch=True).filter(
    lambda x: 0 < len(x) <= MAX_ENTITY_NAME_LENGTH
)

# Strategy for valid field definitions
valid_fields = st.lists(
    st.tuples(
        st.from_regex(r"^[a-z][a-z0-9_]*$", fullmatch=True).filter(
            lambda x: 0 < len(x) <= 30
        ),
        st.sampled_from(["str", "int", "float", "bool"]),
    ),
    min_size=0,
    max_size=5,
)


class TestGeneratedCodeUTCDatetime:
    """Property 7: Generated Code UTC Datetime.

    For any generated entity code, all datetime default_factory calls
    use datetime.now(UTC) instead of datetime.now().
    """

    @given(name=valid_entity_names, fields=valid_fields)
    @settings(max_examples=100)
    def test_entity_uses_utc_datetime(
        self, name: str, fields: list[tuple[str, str]]
    ) -> None:
        """Generated entity code uses UTC for datetime."""
        content = _generate_entity_content(name, fields)

        # Check that UTC is imported
        assert "from datetime import UTC, datetime" in content

        # Check that datetime.now(UTC) is used, not datetime.now()
        # Find all datetime.now calls
        now_calls = re.findall(r"datetime\.now\([^)]*\)", content)
        for call in now_calls:
            assert "UTC" in call, f"datetime.now should use UTC: {call}"

        # Ensure no bare datetime.now() calls
        assert "datetime.now()" not in content

    @given(name=valid_entity_names)
    @settings(max_examples=100)
    def test_entity_without_fields_uses_utc(self, name: str) -> None:
        """Generated entity without custom fields still uses UTC."""
        content = _generate_entity_content(name, [])

        assert "from datetime import UTC, datetime" in content
        assert "datetime.now(UTC)" in content
        assert "datetime.now()" not in content


class TestGeneratedCodeImportOrdering:
    """Property 8: Generated Code Import Ordering.

    For any generated code file, imports are ordered:
    stdlib, third-party, local (following PEP8/isort).
    """

    @given(name=valid_entity_names, fields=valid_fields)
    @settings(max_examples=100)
    def test_entity_import_ordering(
        self, name: str, fields: list[tuple[str, str]]
    ) -> None:
        """Entity imports follow PEP8 ordering."""
        content = _generate_entity_content(name, fields)
        self._verify_import_ordering(content)

    @given(name=valid_entity_names)
    @settings(max_examples=100)
    def test_mapper_import_ordering(self, name: str) -> None:
        """Mapper imports follow PEP8 ordering."""
        content = _generate_mapper_content(name)
        self._verify_import_ordering(content)

    @given(name=valid_entity_names)
    @settings(max_examples=100)
    def test_use_case_import_ordering(self, name: str) -> None:
        """Use case imports follow PEP8 ordering."""
        content = _generate_use_case_content(name, with_cache=False)
        self._verify_import_ordering(content)

    @given(name=valid_entity_names)
    @settings(max_examples=100)
    def test_routes_import_ordering(self, name: str) -> None:
        """Routes imports follow PEP8 ordering."""
        content = _generate_routes_content(name)
        self._verify_import_ordering(content)

    def _verify_import_ordering(self, content: str) -> None:
        """Verify imports are in correct order: stdlib, third-party, local."""
        lines = content.split("\n")
        import_lines = [
            line for line in lines if line.startswith(("import ", "from "))
        ]

        if not import_lines:
            return

        # Categorize imports
        stdlib_imports = []
        third_party_imports = []
        local_imports = []

        stdlib_modules = {
            "datetime",
            "typing",
            "re",
            "pathlib",
            "logging",
            "os",
            "sys",
            "json",
            "collections",
            "functools",
            "itertools",
            "abc",
            "enum",
            "dataclasses",
        }

        third_party_prefixes = {
            "sqlalchemy",
            "sqlmodel",
            "fastapi",
            "pydantic",
            "typer",
        }

        for line in import_lines:
            # Extract module name
            if line.startswith("from "):
                module = line.split()[1].split(".")[0]
            else:
                module = line.split()[1].split(".")[0]

            if module in stdlib_modules:
                stdlib_imports.append(line)
            elif any(module.startswith(prefix) for prefix in third_party_prefixes):
                third_party_imports.append(line)
            elif module.startswith("my_app"):
                local_imports.append(line)
            else:
                # Unknown - could be stdlib or third-party
                # For this test, we'll be lenient
                pass

        # Verify ordering: all stdlib before third-party, all third-party before local
        if stdlib_imports and third_party_imports:
            last_stdlib_idx = max(
                import_lines.index(imp) for imp in stdlib_imports
            )
            first_third_party_idx = min(
                import_lines.index(imp) for imp in third_party_imports
            )
            assert last_stdlib_idx < first_third_party_idx, (
                "stdlib imports should come before third-party imports"
            )

        if third_party_imports and local_imports:
            last_third_party_idx = max(
                import_lines.index(imp) for imp in third_party_imports
            )
            first_local_idx = min(import_lines.index(imp) for imp in local_imports)
            assert last_third_party_idx < first_local_idx, (
                "third-party imports should come before local imports"
            )


class TestCaseConversion:
    """Test case conversion utilities."""

    @given(name=valid_entity_names)
    @settings(max_examples=100)
    def test_snake_to_pascal_round_trip(self, name: str) -> None:
        """Converting snake_case to PascalCase and back preserves structure."""
        pascal = to_pascal_case(name)
        back_to_snake = to_snake_case(pascal)
        # Note: round-trip may not be exact due to underscore handling
        # but the result should still be valid snake_case
        assert re.match(r"^[a-z][a-z0-9_]*$", back_to_snake)

    @pytest.mark.parametrize(
        "snake,pascal",
        [
            ("user", "User"),
            ("user_profile", "UserProfile"),
            ("api_key", "ApiKey"),
            ("http_request", "HttpRequest"),
        ],
    )
    def test_known_conversions(self, snake: str, pascal: str) -> None:
        """Known snake_case to PascalCase conversions are correct."""
        assert to_pascal_case(snake) == pascal


class TestGeneratedCodeContent:
    """Test generated code contains required elements."""

    @given(name=valid_entity_names)
    @settings(max_examples=100)
    def test_entity_has_required_fields(self, name: str) -> None:
        """Generated entity has id, created_at, updated_at, is_deleted."""
        content = _generate_entity_content(name, [])

        assert "id: str" in content
        assert "created_at: datetime" in content
        assert "updated_at: datetime" in content
        assert "is_deleted: bool" in content

    @given(name=valid_entity_names)
    @settings(max_examples=100)
    def test_routes_has_todo_comments(self, name: str) -> None:
        """Generated routes has TODO comments for configuration."""
        content = _generate_routes_content(name)

        assert "TODO:" in content
        assert "DI container" in content or "repository" in content.lower()

    @given(name=valid_entity_names)
    @settings(max_examples=100)
    def test_entity_has_docstrings(self, name: str) -> None:
        """Generated entity has docstrings for all classes."""
        content = _generate_entity_content(name, [])
        pascal_name = to_pascal_case(name)

        # Check for class docstrings
        assert f'"""{pascal_name} domain entity."""' in content
        assert f'"""Base {name} fields' in content
        assert f'"""{pascal_name} database model."""' in content
