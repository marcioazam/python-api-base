"""Property-based tests for code generator.

**Feature: advanced-reusability, Property 14: Code Generation Completeness**
**Validates: Requirements 6.1, 6.4**
"""

import re
import tempfile
from pathlib import Path

from hypothesis import given, settings
from hypothesis import strategies as st

# Import generator functions
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from generate_entity import (
    generate_entity,
    generate_events,
    generate_mapper,
    generate_property_tests,
    generate_routes,
    generate_use_case,
    parse_fields,
    to_pascal_case,
    to_snake_case,
)


# Python reserved words to avoid (lowercase for comparison)
PYTHON_KEYWORDS = {
    "and", "as", "assert", "async", "await", "break", "class", "continue",
    "def", "del", "elif", "else", "except", "finally", "for", "from",
    "global", "if", "import", "in", "is", "lambda", "nonlocal", "not",
    "or", "pass", "raise", "return", "try", "while", "with", "yield",
    "true", "false", "none", "self", "cls",
}

# Strategy for valid entity names (ASCII lowercase only, no keywords)
entity_name_strategy = st.text(
    min_size=3,
    max_size=30,
    alphabet="abcdefghijklmnopqrstuvwxyz",
).filter(lambda x: x.lower() not in PYTHON_KEYWORDS and len(x) >= 3)

# Strategy for field definitions
field_type_strategy = st.sampled_from(["str", "int", "float", "bool"])
field_name_strategy = st.text(
    min_size=3,
    max_size=20,
    alphabet="abcdefghijklmnopqrstuvwxyz",
).filter(lambda x: x.lower() not in PYTHON_KEYWORDS and len(x) >= 3)

field_strategy = st.tuples(field_name_strategy, field_type_strategy)
fields_strategy = st.lists(field_strategy, min_size=0, max_size=5, unique_by=lambda x: x[0])


class TestCodeGenerationCompleteness:
    """Property tests for Code Generation Completeness.

    **Feature: advanced-reusability, Property 14: Code Generation Completeness**
    **Validates: Requirements 6.1, 6.4**
    """

    @settings(max_examples=30)
    @given(name=entity_name_strategy)
    def test_entity_generation_produces_valid_python(self, name: str) -> None:
        """
        **Feature: advanced-reusability, Property 14: Code Generation Completeness**

        For any entity name, the code generator SHALL produce syntactically
        valid Python code for the entity file.
        """
        code = generate_entity(name, [])
        
        # Should compile without syntax errors
        compile(code, f"{name}.py", "exec")
        
        # Should contain required classes
        pascal_name = to_pascal_case(name)
        assert f"class {pascal_name}Base" in code
        assert f"class {pascal_name}(" in code
        assert f"class {pascal_name}Create" in code
        assert f"class {pascal_name}Update" in code
        assert f"class {pascal_name}Response" in code

    @settings(max_examples=30)
    @given(name=entity_name_strategy, fields=fields_strategy)
    def test_entity_with_fields_includes_all_fields(
        self, name: str, fields: list[tuple[str, str]]
    ) -> None:
        """
        For any entity with fields, all field definitions SHALL be included.
        """
        code = generate_entity(name, fields)
        
        # Should compile
        compile(code, f"{name}.py", "exec")
        
        # All fields should be present
        for field_name, field_type in fields:
            assert field_name in code

    @settings(max_examples=30)
    @given(name=entity_name_strategy)
    def test_mapper_generation_produces_valid_python(self, name: str) -> None:
        """
        For any entity name, the mapper generator SHALL produce valid Python.
        """
        code = generate_mapper(name)
        
        # Should compile
        compile(code, f"{name}_mapper.py", "exec")
        
        # Should contain mapper class
        pascal_name = to_pascal_case(name)
        assert f"class {pascal_name}Mapper" in code

    @settings(max_examples=30)
    @given(name=entity_name_strategy)
    def test_use_case_generation_produces_valid_python(self, name: str) -> None:
        """
        For any entity name, the use case generator SHALL produce valid Python.
        """
        code = generate_use_case(name, with_cache=False)
        
        # Should compile
        compile(code, f"{name}_use_case.py", "exec")
        
        # Should contain use case class
        pascal_name = to_pascal_case(name)
        assert f"class {pascal_name}UseCase" in code

    @settings(max_examples=20)
    @given(name=entity_name_strategy)
    def test_use_case_with_cache_includes_decorator(self, name: str) -> None:
        """
        When --with-cache is specified, use case SHALL include @cached decorator.
        """
        code = generate_use_case(name, with_cache=True)
        
        # Should compile
        compile(code, f"{name}_use_case.py", "exec")
        
        # Should include caching
        assert "from my_api.shared.caching import cached" in code
        assert "@cached" in code

    @settings(max_examples=30)
    @given(name=entity_name_strategy)
    def test_routes_generation_produces_valid_python(self, name: str) -> None:
        """
        For any entity name, the routes generator SHALL produce valid Python.
        """
        code = generate_routes(name)
        
        # Should compile
        compile(code, f"{name}s.py", "exec")
        
        # Should contain router
        assert "GenericCRUDRouter" in code
        assert f"/{name}s" in code

    @settings(max_examples=30)
    @given(name=entity_name_strategy)
    def test_events_generation_produces_valid_python(self, name: str) -> None:
        """
        For any entity name, the events generator SHALL produce valid Python.
        """
        code = generate_events(name)
        
        # Should compile
        compile(code, f"{name}_events.py", "exec")
        
        # Should contain event classes
        pascal_name = to_pascal_case(name)
        assert f"class {pascal_name}Created" in code
        assert f"class {pascal_name}Updated" in code
        assert f"class {pascal_name}Deleted" in code

    @settings(max_examples=30)
    @given(name=entity_name_strategy, fields=fields_strategy)
    def test_property_tests_generation_produces_valid_python(
        self, name: str, fields: list[tuple[str, str]]
    ) -> None:
        """
        For any entity, the test generator SHALL produce valid Python test code.
        """
        code = generate_property_tests(name, fields)
        
        # Should compile
        compile(code, f"test_{name}_properties.py", "exec")
        
        # Should contain test class
        pascal_name = to_pascal_case(name)
        assert f"class Test{pascal_name}Properties" in code
        assert "hypothesis" in code

    @settings(max_examples=20)
    @given(name=entity_name_strategy)
    def test_all_required_files_generated(self, name: str) -> None:
        """
        **Feature: advanced-reusability, Property 14: Code Generation Completeness**

        For any entity name, the code generator SHALL produce all required
        files (entity, repository, use case, mapper, routes, tests).
        """
        # Generate all files
        entity_code = generate_entity(name, [])
        mapper_code = generate_mapper(name)
        use_case_code = generate_use_case(name)
        routes_code = generate_routes(name)
        tests_code = generate_property_tests(name, [])
        events_code = generate_events(name)
        
        # All should be non-empty and valid Python
        for code in [entity_code, mapper_code, use_case_code, routes_code, tests_code, events_code]:
            assert len(code) > 0
            compile(code, "test.py", "exec")


class TestNameConversions:
    """Tests for name conversion utilities."""

    @settings(max_examples=50)
    @given(name=entity_name_strategy)
    def test_snake_to_pascal_conversion(self, name: str) -> None:
        """Snake case names SHALL convert to PascalCase correctly."""
        pascal = to_pascal_case(name)
        
        # Should start with uppercase
        assert pascal[0].isupper()
        
        # Should not contain underscores
        assert "_" not in pascal

    @settings(max_examples=50)
    @given(name=st.from_regex(r"[A-Z][a-z]+([A-Z][a-z]+)*", fullmatch=True))
    def test_pascal_to_snake_conversion(self, name: str) -> None:
        """PascalCase names SHALL convert to snake_case correctly."""
        snake = to_snake_case(name)
        
        # Should be lowercase
        assert snake == snake.lower()

    def test_round_trip_conversion(self) -> None:
        """Converting snake -> pascal -> snake SHALL preserve the name."""
        original = "my_entity_name"
        pascal = to_pascal_case(original)
        back = to_snake_case(pascal)
        
        assert back == original


class TestFieldParsing:
    """Tests for field parsing."""

    def test_parse_empty_fields(self) -> None:
        """Empty string SHALL return empty list."""
        assert parse_fields("") == []

    def test_parse_single_field(self) -> None:
        """Single field SHALL be parsed correctly."""
        result = parse_fields("name:str")
        assert result == [("name", "str")]

    def test_parse_multiple_fields(self) -> None:
        """Multiple fields SHALL be parsed correctly."""
        result = parse_fields("name:str,price:float,active:bool")
        assert result == [("name", "str"), ("price", "float"), ("active", "bool")]

    def test_parse_fields_with_spaces(self) -> None:
        """Fields with spaces SHALL be trimmed."""
        result = parse_fields(" name : str , price : float ")
        assert result == [("name", "str"), ("price", "float")]

    @settings(max_examples=30)
    @given(fields=fields_strategy)
    def test_parse_fields_round_trip(self, fields: list[tuple[str, str]]) -> None:
        """Parsing formatted fields SHALL return original fields."""
        if not fields:
            return
            
        fields_str = ",".join(f"{name}:{ftype}" for name, ftype in fields)
        result = parse_fields(fields_str)
        
        assert result == fields
