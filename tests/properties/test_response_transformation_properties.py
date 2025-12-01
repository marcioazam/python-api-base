"""Property-based tests for Response Transformation Pattern.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.3**
"""

from datetime import datetime

import pytest
from hypothesis import given, settings, strategies as st

from my_app.interface.api.response_transformation import (
    ClientTypeTransformer,
    CompositeTransformer,
    FieldAddTransformer,
    FieldRemoveTransformer,
    FieldRenameTransformer,
    FieldTransformTransformer,
    IdentityTransformer,
    ResponseTransformer,
    TransformationBuilder,
    TransformationContext,
    VersionedTransformer,
    camel_to_snake,
    convert_keys_to_camel,
    convert_keys_to_snake,
    create_response_transformer,
    snake_to_camel,
    transform_for_client,
    transform_for_version,
)


# Strategies
field_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=20,
).filter(lambda x: x.strip() and x.isalpha())

dict_data_strategy = st.dictionaries(
    keys=field_name_strategy,
    values=st.integers(),
    min_size=1,
    max_size=10,
)


class TestTransformationContextProperties:
    """Property tests for TransformationContext."""

    @given(
        api_version=st.text(min_size=0, max_size=10),
        client_type=st.text(min_size=0, max_size=20),
        locale=st.sampled_from(["en", "es", "fr", "de", "pt"]),
    )
    @settings(max_examples=100)
    def test_context_preserves_values(
        self, api_version: str, client_type: str, locale: str
    ) -> None:
        """Property: Context preserves all values."""
        context = TransformationContext(
            api_version=api_version,
            client_type=client_type,
            locale=locale,
        )
        assert context.api_version == api_version
        assert context.client_type == client_type
        assert context.locale == locale


class TestIdentityTransformerProperties:
    """Property tests for IdentityTransformer."""

    @given(data=dict_data_strategy)
    @settings(max_examples=100)
    def test_identity_returns_unchanged_data(
        self, data: dict[str, int]
    ) -> None:
        """Property: IdentityTransformer returns data unchanged."""
        transformer = IdentityTransformer[dict[str, int]]()
        context = TransformationContext()
        result = transformer.transform(data, context)
        assert result == data

    def test_identity_always_can_transform(self) -> None:
        """Property: IdentityTransformer always can transform."""
        transformer = IdentityTransformer[dict[str, int]]()
        context = TransformationContext()
        assert transformer.can_transform(context) is True


class TestFieldRenameTransformerProperties:
    """Property tests for FieldRenameTransformer."""

    @given(data=dict_data_strategy)
    @settings(max_examples=100)
    def test_rename_changes_keys(self, data: dict[str, int]) -> None:
        """Property: Rename transformer changes specified keys."""
        if not data:
            return

        old_key = list(data.keys())[0]
        new_key = f"renamed_{old_key}"
        renames = {old_key: new_key}

        transformer = FieldRenameTransformer(renames)
        context = TransformationContext()
        result = transformer.transform(data, context)

        assert old_key not in result
        assert new_key in result
        assert result[new_key] == data[old_key]

    @given(data=dict_data_strategy)
    @settings(max_examples=100)
    def test_rename_preserves_unrenamed_keys(
        self, data: dict[str, int]
    ) -> None:
        """Property: Unrenamed keys are preserved."""
        transformer = FieldRenameTransformer({})
        context = TransformationContext()
        result = transformer.transform(data, context)
        assert result == data


class TestFieldRemoveTransformerProperties:
    """Property tests for FieldRemoveTransformer."""

    @given(data=dict_data_strategy)
    @settings(max_examples=100)
    def test_remove_removes_specified_fields(
        self, data: dict[str, int]
    ) -> None:
        """Property: Remove transformer removes specified fields."""
        if not data:
            return

        key_to_remove = list(data.keys())[0]
        transformer = FieldRemoveTransformer({key_to_remove})
        context = TransformationContext()
        result = transformer.transform(data, context)

        assert key_to_remove not in result
        assert len(result) == len(data) - 1

    @given(data=dict_data_strategy)
    @settings(max_examples=100)
    def test_remove_preserves_other_fields(
        self, data: dict[str, int]
    ) -> None:
        """Property: Non-removed fields are preserved."""
        transformer = FieldRemoveTransformer(set())
        context = TransformationContext()
        result = transformer.transform(data, context)
        assert result == data


class TestFieldAddTransformerProperties:
    """Property tests for FieldAddTransformer."""

    @given(
        data=dict_data_strategy,
        new_value=st.integers(),
    )
    @settings(max_examples=100)
    def test_add_adds_new_fields(
        self, data: dict[str, int], new_value: int
    ) -> None:
        """Property: Add transformer adds new fields."""
        new_field = "new_field"
        transformer = FieldAddTransformer({new_field: new_value})
        context = TransformationContext()
        result = transformer.transform(data, context)

        assert new_field in result
        assert result[new_field] == new_value

    def test_add_with_callable(self) -> None:
        """Property: Add transformer works with callable."""
        data = {"value": 10}

        def compute_fields(d: dict[str, int]) -> dict[str, int]:
            return {"doubled": d.get("value", 0) * 2}

        transformer = FieldAddTransformer(compute_fields)
        context = TransformationContext()
        result = transformer.transform(data, context)

        assert result["doubled"] == 20



class TestFieldTransformTransformerProperties:
    """Property tests for FieldTransformTransformer."""

    def test_transform_applies_to_specified_fields(self) -> None:
        """Property: Transform applies to specified fields."""
        data = {"value": 10, "other": 5}
        transformer = FieldTransformTransformer({"value": lambda x: x * 2})
        context = TransformationContext()
        result = transformer.transform(data, context)

        assert result["value"] == 20
        assert result["other"] == 5

    @given(data=dict_data_strategy)
    @settings(max_examples=100)
    def test_transform_preserves_untransformed_fields(
        self, data: dict[str, int]
    ) -> None:
        """Property: Untransformed fields are preserved."""
        transformer = FieldTransformTransformer({})
        context = TransformationContext()
        result = transformer.transform(data, context)
        assert result == data


class TestVersionedTransformerProperties:
    """Property tests for VersionedTransformer."""

    def test_applies_within_version_range(self) -> None:
        """Property: Applies when version is within range."""
        inner = FieldRemoveTransformer({"secret"})
        transformer = VersionedTransformer(
            min_version="1.0",
            max_version="2.0",
            transformer=inner,
        )

        context = TransformationContext(api_version="1.5")
        assert transformer.can_transform(context) is True

    def test_does_not_apply_outside_version_range(self) -> None:
        """Property: Does not apply when version is outside range."""
        inner = FieldRemoveTransformer({"secret"})
        transformer = VersionedTransformer(
            min_version="2.0",
            max_version="3.0",
            transformer=inner,
        )

        context = TransformationContext(api_version="1.0")
        assert transformer.can_transform(context) is False


class TestClientTypeTransformerProperties:
    """Property tests for ClientTypeTransformer."""

    def test_applies_for_matching_client(self) -> None:
        """Property: Applies when client type matches."""
        inner = FieldRemoveTransformer({"internal"})
        transformer = ClientTypeTransformer({"mobile", "web"}, inner)

        context = TransformationContext(client_type="mobile")
        assert transformer.can_transform(context) is True

    def test_does_not_apply_for_non_matching_client(self) -> None:
        """Property: Does not apply when client type doesn't match."""
        inner = FieldRemoveTransformer({"internal"})
        transformer = ClientTypeTransformer({"mobile"}, inner)

        context = TransformationContext(client_type="desktop")
        assert transformer.can_transform(context) is False


class TestCompositeTransformerProperties:
    """Property tests for CompositeTransformer."""

    def test_chains_transformers(self) -> None:
        """Property: Chains multiple transformers."""
        t1 = FieldRenameTransformer({"old": "new"})
        t2 = FieldAddTransformer({"added": 42})

        composite = CompositeTransformer([t1, t2])
        context = TransformationContext()
        result = composite.transform({"old": 1}, context)

        assert "new" in result
        assert "added" in result
        assert result["new"] == 1
        assert result["added"] == 42

    def test_add_returns_self(self) -> None:
        """Property: add() returns self for chaining."""
        composite = CompositeTransformer()
        result = composite.add(IdentityTransformer())
        assert result is composite


class TestResponseTransformerProperties:
    """Property tests for ResponseTransformer."""

    def test_applies_general_transformers(self) -> None:
        """Property: Applies general transformers."""
        transformer = ResponseTransformer[dict]()
        transformer.add_transformer(FieldAddTransformer({"added": 1}))

        context = TransformationContext()
        result = transformer.transform({"original": 0}, context)

        assert result["added"] == 1
        assert result["original"] == 0

    def test_applies_version_specific_transformer(self) -> None:
        """Property: Applies version-specific transformer."""
        transformer = ResponseTransformer[dict]()
        transformer.for_version("v2", FieldAddTransformer({"v2_field": True}))

        context = TransformationContext(api_version="v2")
        result = transformer.transform({}, context)

        assert result["v2_field"] is True

    def test_applies_client_specific_transformer(self) -> None:
        """Property: Applies client-specific transformer."""
        transformer = ResponseTransformer[dict]()
        transformer.for_client("mobile", FieldRemoveTransformer({"desktop_only"}))

        context = TransformationContext(client_type="mobile")
        result = transformer.transform({"desktop_only": 1, "shared": 2}, context)

        assert "desktop_only" not in result
        assert result["shared"] == 2


class TestTransformationBuilderProperties:
    """Property tests for TransformationBuilder."""

    def test_builder_fluent_interface(self) -> None:
        """Property: Builder methods return builder for chaining."""
        builder = TransformationBuilder()
        result = (
            builder
            .rename_fields({"a": "b"})
            .remove_fields({"c"})
            .add_fields({"d": 1})
        )
        assert result is builder

    def test_builder_creates_working_transformer(self) -> None:
        """Property: Builder creates working transformer."""
        transformer = (
            TransformationBuilder()
            .rename_fields({"old": "new"})
            .add_fields({"added": 42})
            .build()
        )

        context = TransformationContext()
        result = transformer.transform({"old": 1}, context)

        assert result["new"] == 1
        assert result["added"] == 42


class TestCaseConversionProperties:
    """Property tests for case conversion functions."""

    @given(
        name=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1,
            max_size=20,
        ).filter(lambda x: x.islower())
    )
    @settings(max_examples=100)
    def test_snake_to_camel_lowercase_unchanged(self, name: str) -> None:
        """Property: Single word lowercase stays lowercase."""
        if "_" not in name:
            result = snake_to_camel(name)
            assert result == name

    def test_snake_to_camel_converts_correctly(self) -> None:
        """Property: snake_case converts to camelCase."""
        assert snake_to_camel("hello_world") == "helloWorld"
        assert snake_to_camel("user_id") == "userId"
        assert snake_to_camel("created_at") == "createdAt"

    def test_camel_to_snake_converts_correctly(self) -> None:
        """Property: camelCase converts to snake_case."""
        assert camel_to_snake("helloWorld") == "hello_world"
        assert camel_to_snake("userId") == "user_id"
        assert camel_to_snake("createdAt") == "created_at"

    def test_convert_keys_to_camel(self) -> None:
        """Property: convert_keys_to_camel converts all keys."""
        data = {"user_id": 1, "created_at": "2023-01-01"}
        result = convert_keys_to_camel(data)

        assert "userId" in result
        assert "createdAt" in result
        assert "user_id" not in result

    def test_convert_keys_to_snake(self) -> None:
        """Property: convert_keys_to_snake converts all keys."""
        data = {"userId": 1, "createdAt": "2023-01-01"}
        result = convert_keys_to_snake(data)

        assert "user_id" in result
        assert "created_at" in result
        assert "userId" not in result


class TestConvenienceFunctions:
    """Property tests for convenience functions."""

    def test_create_response_transformer(self) -> None:
        """Property: create_response_transformer returns transformer."""
        transformer = create_response_transformer()
        assert isinstance(transformer, ResponseTransformer)

    def test_transform_for_version(self) -> None:
        """Property: transform_for_version applies correct transformer."""
        transformations = {
            "v1": FieldAddTransformer({"v1": True}),
            "v2": FieldAddTransformer({"v2": True}),
        }

        result = transform_for_version({}, "v1", transformations)
        assert result["v1"] is True

    def test_transform_for_client(self) -> None:
        """Property: transform_for_client applies correct transformer."""
        transformations = {
            "mobile": FieldAddTransformer({"mobile": True}),
            "web": FieldAddTransformer({"web": True}),
        }

        result = transform_for_client({}, "mobile", transformations)
        assert result["mobile"] is True
