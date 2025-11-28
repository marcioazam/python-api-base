"""Property-based tests for SDK Generator.

**Feature: api-architecture-analysis, Property: SDK generation**
**Validates: Requirements 18.2**
"""

import pytest
from hypothesis import given, strategies as st, settings

from my_api.shared.sdk_generator import (
    SDKGenerator,
    SDKConfig,
    SDKLanguage,
)


@st.composite
def openapi_schema_strategy(draw: st.DrawFn) -> dict:
    """Generate valid OpenAPI schema."""
    schema_name = draw(st.text(
        alphabet="ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz",
        min_size=3,
        max_size=20
    ))
    properties = {}
    prop_count = draw(st.integers(min_value=1, max_value=5))
    for i in range(prop_count):
        prop_name = f"field{i}"
        prop_type = draw(st.sampled_from(["string", "integer", "boolean"]))
        properties[prop_name] = {"type": prop_type}

    return {
        "info": {"title": "Test API", "version": "1.0.0"},
        "paths": {},
        "components": {
            "schemas": {
                schema_name: {
                    "type": "object",
                    "properties": properties
                }
            }
        }
    }


class TestSDKGeneratorProperties:
    """Property tests for SDK generator."""

    @given(openapi_schema_strategy())
    @settings(max_examples=50)
    def test_typescript_generates_package_json(self, spec: dict) -> None:
        """TypeScript SDK includes package.json."""
        generator = SDKGenerator(spec)
        config = SDKConfig(
            language=SDKLanguage.TYPESCRIPT,
            package_name="test-sdk",
            version="1.0.0"
        )
        files = generator.generate(config)

        paths = [f.path for f in files]
        assert "package.json" in paths

    @given(openapi_schema_strategy())
    @settings(max_examples=50)
    def test_typescript_generates_types(self, spec: dict) -> None:
        """TypeScript SDK includes type definitions."""
        generator = SDKGenerator(spec)
        config = SDKConfig(
            language=SDKLanguage.TYPESCRIPT,
            package_name="test-sdk"
        )
        files = generator.generate(config)

        types_file = next((f for f in files if "types" in f.path), None)
        assert types_file is not None
        assert "interface" in types_file.content

    @given(openapi_schema_strategy())
    @settings(max_examples=50)
    def test_python_generates_pyproject(self, spec: dict) -> None:
        """Python SDK includes pyproject.toml."""
        generator = SDKGenerator(spec)
        config = SDKConfig(
            language=SDKLanguage.PYTHON,
            package_name="test-sdk"
        )
        files = generator.generate(config)

        paths = [f.path for f in files]
        assert "pyproject.toml" in paths

    @given(openapi_schema_strategy())
    @settings(max_examples=50)
    def test_python_generates_models(self, spec: dict) -> None:
        """Python SDK includes Pydantic models."""
        generator = SDKGenerator(spec)
        config = SDKConfig(
            language=SDKLanguage.PYTHON,
            package_name="test-sdk"
        )
        files = generator.generate(config)

        models_file = next((f for f in files if "models" in f.path), None)
        assert models_file is not None
        assert "BaseModel" in models_file.content

    @given(openapi_schema_strategy())
    @settings(max_examples=50)
    def test_go_generates_go_mod(self, spec: dict) -> None:
        """Go SDK includes go.mod."""
        generator = SDKGenerator(spec)
        config = SDKConfig(
            language=SDKLanguage.GO,
            package_name="test-sdk"
        )
        files = generator.generate(config)

        paths = [f.path for f in files]
        assert "go.mod" in paths

    @given(
        openapi_schema_strategy(),
        st.sampled_from([SDKLanguage.TYPESCRIPT, SDKLanguage.PYTHON, SDKLanguage.GO])
    )
    @settings(max_examples=30)
    def test_all_files_have_correct_language(
        self,
        spec: dict,
        language: SDKLanguage
    ) -> None:
        """All generated files have correct language tag."""
        generator = SDKGenerator(spec)
        config = SDKConfig(language=language, package_name="test-sdk")
        files = generator.generate(config)

        for file in files:
            assert file.language == language
