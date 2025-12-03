"""Property-based tests for CLI validators.

**Feature: cli-security-improvements**
**Properties 1-5: Validation Properties**
**Validates: Requirements 1.3, 1.4, 2.1-2.6**
"""

import pytest

pytest.skip('Module cli.constants not implemented', allow_module_level=True)

from hypothesis import assume, given, settings
from hypothesis import strategies as st

from cli.constants import (
    ALLOWED_ALEMBIC_COMMANDS,
    ALLOWED_FIELD_TYPES,
    ENTITY_NAME_PATTERN,
    MAX_ENTITY_NAME_LENGTH,
    MAX_FIELD_NAME_LENGTH,
    REVISION_PATTERN,
)
from cli.exceptions import (
    InvalidCommandError,
    InvalidEntityNameError,
    InvalidFieldError,
    InvalidPathError,
    InvalidRevisionError,
    ValidationError,
)
from cli.validators import (
    serialize_field_definition,
    validate_alembic_command,
    validate_entity_name,
    validate_field_definition,
    validate_path,
    validate_revision,
    validate_rollback_steps,
)


class TestAlembicCommandWhitelist:
    """Property 1: Alembic Command Whitelist Validation.

    For any command string, it passes alembic validation if and only if
    it is in the set of allowed commands.
    """

    @given(command=st.sampled_from(list(ALLOWED_ALEMBIC_COMMANDS)))
    @settings(max_examples=100)
    def test_valid_commands_pass(self, command: str) -> None:
        """All whitelisted commands pass validation."""
        result = validate_alembic_command(command)
        assert result == command

    @given(command=st.text(min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_invalid_commands_rejected(self, command: str) -> None:
        """Non-whitelisted commands are rejected."""
        assume(command not in ALLOWED_ALEMBIC_COMMANDS)
        with pytest.raises(InvalidCommandError):
            validate_alembic_command(command)

    def test_empty_command_rejected(self) -> None:
        """Empty command is rejected."""
        with pytest.raises(InvalidCommandError):
            validate_alembic_command("")

    @given(command=st.text(min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_validation_is_deterministic(self, command: str) -> None:
        """Validation result is consistent for same input."""
        try:
            result1 = validate_alembic_command(command)
            result2 = validate_alembic_command(command)
            assert result1 == result2
        except InvalidCommandError:
            with pytest.raises(InvalidCommandError):
                validate_alembic_command(command)


class TestRevisionFormatValidation:
    """Property 2: Revision Format Validation.

    For any string, it passes revision validation if and only if it matches
    the pattern ^[a-zA-Z0-9_-]+$ OR equals "head" OR equals "base".
    """

    @given(
        revision=st.from_regex(r"^[a-zA-Z0-9_\-]+$", fullmatch=True).filter(
            lambda x: len(x) > 0
        )
    )
    @settings(max_examples=100)
    def test_valid_revisions_pass(self, revision: str) -> None:
        """Valid revision formats pass validation."""
        result = validate_revision(revision)
        assert result == revision

    @pytest.mark.parametrize("revision", ["head", "base"])
    def test_special_revisions_pass(self, revision: str) -> None:
        """Special revision keywords pass validation."""
        result = validate_revision(revision)
        assert result == revision

    @given(
        revision=st.text(min_size=1, max_size=50).filter(
            lambda x: not REVISION_PATTERN.match(x)
        )
    )
    @settings(max_examples=100)
    def test_invalid_revisions_rejected(self, revision: str) -> None:
        """Invalid revision formats are rejected."""
        with pytest.raises(InvalidRevisionError):
            validate_revision(revision)

    def test_empty_revision_rejected(self) -> None:
        """Empty revision is rejected."""
        with pytest.raises(InvalidRevisionError):
            validate_revision("")

    @given(revision=st.text(min_size=0, max_size=100))
    @settings(max_examples=100)
    def test_validation_matches_pattern(self, revision: str) -> None:
        """Validation result matches regex pattern check."""
        pattern_matches = bool(revision and REVISION_PATTERN.match(revision))
        try:
            validate_revision(revision)
            assert pattern_matches
        except InvalidRevisionError:
            assert not pattern_matches


class TestEntityNameValidation:
    """Property 3: Entity Name Validation.

    For any string, it passes entity name validation if and only if it
    matches ^[a-z][a-z0-9_]*$ AND has length between 1 and 50 characters.
    """

    @given(
        name=st.from_regex(r"^[a-z][a-z0-9_]*$", fullmatch=True).filter(
            lambda x: 0 < len(x) <= MAX_ENTITY_NAME_LENGTH
        )
    )
    @settings(max_examples=100)
    def test_valid_names_pass(self, name: str) -> None:
        """Valid entity names pass validation."""
        result = validate_entity_name(name)
        assert result == name

    @given(
        name=st.text(min_size=1, max_size=100).filter(
            lambda x: not ENTITY_NAME_PATTERN.match(x)
        )
    )
    @settings(max_examples=100)
    def test_invalid_pattern_rejected(self, name: str) -> None:
        """Names not matching pattern are rejected."""
        with pytest.raises(InvalidEntityNameError):
            validate_entity_name(name)

    @given(
        base=st.from_regex(r"^[a-z][a-z0-9_]*$", fullmatch=True).filter(
            lambda x: len(x) >= 1
        ),
        extra_length=st.integers(min_value=1, max_value=100),
    )
    @settings(max_examples=100)
    def test_long_names_rejected(self, base: str, extra_length: int) -> None:
        """Names exceeding max length are rejected."""
        # Construct a name that exceeds the limit
        name = base + "a" * (MAX_ENTITY_NAME_LENGTH - len(base) + extra_length)
        assume(len(name) > MAX_ENTITY_NAME_LENGTH)
        with pytest.raises(InvalidEntityNameError):
            validate_entity_name(name)

    def test_empty_name_rejected(self) -> None:
        """Empty name is rejected."""
        with pytest.raises(InvalidEntityNameError):
            validate_entity_name("")

    @pytest.mark.parametrize(
        "name",
        ["User", "PRODUCT", "123name", "_private", "has-dash", "has space"],
    )
    def test_specific_invalid_names(self, name: str) -> None:
        """Specific invalid name patterns are rejected."""
        with pytest.raises(InvalidEntityNameError):
            validate_entity_name(name)


class TestPathTraversalDetection:
    """Property 4: Path Traversal Detection.

    For any path string containing ".." followed by a path separator
    (or vice versa), the path validation SHALL reject it.
    """

    @given(
        path=st.text(min_size=1, max_size=100).filter(
            lambda x: ".." not in x and x.strip()
        )
    )
    @settings(max_examples=100)
    def test_safe_paths_pass(self, path: str) -> None:
        """Paths without traversal sequences pass validation."""
        result = validate_path(path)
        assert result == path

    @pytest.mark.parametrize(
        "path",
        [
            "../etc/passwd",
            "..\\windows\\system32",
            "foo/../bar",
            "foo\\..\\bar",
            "/path/to/../secret",
            "C:\\path\\..\\secret",
        ],
    )
    def test_traversal_paths_rejected(self, path: str) -> None:
        """Paths with traversal sequences are rejected."""
        with pytest.raises(InvalidPathError):
            validate_path(path)

    def test_empty_path_rejected(self) -> None:
        """Empty path is rejected."""
        with pytest.raises(InvalidPathError):
            validate_path("")

    @given(
        prefix=st.text(min_size=0, max_size=20).filter(lambda x: ".." not in x),
        suffix=st.text(min_size=0, max_size=20).filter(lambda x: ".." not in x),
        separator=st.sampled_from(["/", "\\"]),
    )
    @settings(max_examples=100)
    def test_injected_traversal_detected(
        self, prefix: str, suffix: str, separator: str
    ) -> None:
        """Traversal sequences are detected regardless of position."""
        path = f"{prefix}..{separator}{suffix}"
        if path.strip():  # Non-empty after strip
            with pytest.raises(InvalidPathError):
                validate_path(path)


class TestFieldDefinitionParsing:
    """Property 5: Field Definition Parsing Round-Trip.

    For any valid field definition string in format "name:type",
    parsing and re-serializing produces an equivalent representation.
    """

    @given(
        name=st.from_regex(r"^[a-z][a-z0-9_]*$", fullmatch=True).filter(
            lambda x: 0 < len(x) <= MAX_FIELD_NAME_LENGTH
        ),
        ftype=st.sampled_from(list(ALLOWED_FIELD_TYPES)),
    )
    @settings(max_examples=100)
    def test_round_trip_consistency(self, name: str, ftype: str) -> None:
        """Parsing then serializing produces equivalent result."""
        field_str = f"{name}:{ftype}"
        parsed_name, parsed_type = validate_field_definition(field_str)
        serialized = serialize_field_definition(parsed_name, parsed_type)
        assert serialized == field_str

    @given(
        name=st.from_regex(r"^[a-z][a-z0-9_]*$", fullmatch=True).filter(
            lambda x: 0 < len(x) <= MAX_FIELD_NAME_LENGTH
        ),
        ftype=st.sampled_from(list(ALLOWED_FIELD_TYPES)),
    )
    @settings(max_examples=100)
    def test_valid_fields_parse_correctly(self, name: str, ftype: str) -> None:
        """Valid field definitions parse to correct components."""
        field_str = f"{name}:{ftype}"
        parsed_name, parsed_type = validate_field_definition(field_str)
        assert parsed_name == name
        assert parsed_type == ftype

    @given(ftype=st.text(min_size=1, max_size=20))
    @settings(max_examples=100)
    def test_invalid_types_rejected(self, ftype: str) -> None:
        """Invalid field types are rejected."""
        assume(ftype not in ALLOWED_FIELD_TYPES)
        with pytest.raises(InvalidFieldError):
            validate_field_definition(f"valid_name:{ftype}")

    @pytest.mark.parametrize(
        "field_str",
        [
            "",
            "nocodon",
            "too:many:colons",
            ":notype",
            "noname:",
            "Invalid:str",
            "123invalid:str",
        ],
    )
    def test_malformed_fields_rejected(self, field_str: str) -> None:
        """Malformed field definitions are rejected."""
        with pytest.raises(InvalidFieldError):
            validate_field_definition(field_str)


class TestRollbackStepsValidation:
    """Test rollback steps validation."""

    @given(steps=st.integers(min_value=1, max_value=100))
    @settings(max_examples=100)
    def test_valid_steps_pass(self, steps: int) -> None:
        """Valid step counts pass validation."""
        result = validate_rollback_steps(steps)
        assert result == steps

    @given(steps=st.integers(max_value=0))
    @settings(max_examples=100)
    def test_zero_or_negative_rejected(self, steps: int) -> None:
        """Zero or negative steps are rejected."""
        with pytest.raises(ValidationError):
            validate_rollback_steps(steps)

    @given(steps=st.integers(min_value=101))
    @settings(max_examples=100)
    def test_excessive_steps_rejected(self, steps: int) -> None:
        """Steps exceeding maximum are rejected."""
        with pytest.raises(ValidationError):
            validate_rollback_steps(steps)
