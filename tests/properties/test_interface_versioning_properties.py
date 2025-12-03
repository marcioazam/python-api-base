"""Property-based tests for interface versioning module.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 1.1, 1.2**
"""

import pytest
from datetime import datetime, timezone
from hypothesis import given, settings, assume
from hypothesis import strategies as st
from pydantic import BaseModel

from interface.versioning import (
    ApiVersion,
    VersionConfig,
    VersionedRouter,
    VersionFormat,
    VersionRouter,
    BaseResponseTransformer,
    deprecated,
)


# =============================================================================
# Strategies
# =============================================================================

version_int_strategy = st.integers(min_value=1, max_value=100)
version_str_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=10,
)
prefix_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=0,
    max_size=20,
).map(lambda x: f"/{x}" if x else "")


# =============================================================================
# Property 7: ApiVersion Immutability
# =============================================================================


class TestApiVersionImmutability:
    """Property tests for ApiVersion immutability.

    **Feature: interface-modules-workflow-analysis, Property 7: ApiVersion Immutability**
    **Validates: Requirements 1.1**
    """

    @given(version=version_int_strategy)
    @settings(max_examples=100)
    def test_api_version_is_frozen(self, version: int) -> None:
        """ApiVersion SHALL be immutable (frozen dataclass)."""
        api_version = ApiVersion[int](version=version)

        with pytest.raises(AttributeError):
            api_version.version = version + 1

    @given(version=version_int_strategy, deprecated=st.booleans())
    @settings(max_examples=100)
    def test_api_version_deprecated_is_frozen(
        self, version: int, deprecated: bool
    ) -> None:
        """ApiVersion deprecated field SHALL be immutable."""
        api_version = ApiVersion[int](version=version, deprecated=deprecated)

        with pytest.raises(AttributeError):
            api_version.deprecated = not deprecated

    @given(version=version_int_strategy)
    @settings(max_examples=100)
    def test_api_version_preserves_values(self, version: int) -> None:
        """ApiVersion SHALL preserve all provided values."""
        sunset = datetime.now(timezone.utc)
        successor = version + 1

        api_version = ApiVersion[int](
            version=version,
            deprecated=True,
            sunset_date=sunset,
            successor=successor,
        )

        assert api_version.version == version
        assert api_version.deprecated is True
        assert api_version.sunset_date == sunset
        assert api_version.successor == successor


# =============================================================================
# Property 8: VersionedRouter Prefix Format
# =============================================================================


class TestVersionedRouterPrefixFormat:
    """Property tests for VersionedRouter prefix format.

    **Feature: interface-modules-workflow-analysis, Property 8: VersionedRouter Prefix Format**
    **Validates: Requirements 1.2**
    """

    @given(version=version_int_strategy)
    @settings(max_examples=100)
    def test_versioned_router_prefix_format(self, version: int) -> None:
        """VersionedRouter prefix SHALL be '/vV{original_prefix}'."""
        api_version = ApiVersion[int](version=version)
        router = VersionedRouter[int](version=api_version)

        assert router.router.prefix == f"/v{version}"

    @given(version=version_int_strategy, prefix=prefix_strategy)
    @settings(max_examples=100)
    def test_versioned_router_with_custom_prefix(
        self, version: int, prefix: str
    ) -> None:
        """VersionedRouter SHALL include custom prefix after version."""
        api_version = ApiVersion[int](version=version)
        router = VersionedRouter[int](version=api_version, prefix=prefix)

        expected_prefix = f"/v{version}{prefix}"
        assert router.router.prefix == expected_prefix

    @given(version=version_str_strategy)
    @settings(max_examples=100)
    def test_versioned_router_with_string_version(self, version: str) -> None:
        """VersionedRouter SHALL work with string versions."""
        assume(len(version.strip()) > 0)
        api_version = ApiVersion[str](version=version)
        router = VersionedRouter[str](version=api_version)

        assert router.router.prefix == f"/v{version}"


# =============================================================================
# Property 9: ResponseTransformer Field Mapping
# =============================================================================


class SourceModel(BaseModel):
    """Source model for transformer tests."""

    old_name: str
    value: int
    unchanged: str


class TargetModel(BaseModel):
    """Target model for transformer tests."""

    new_name: str
    value: int
    unchanged: str


class TestResponseTransformerFieldMapping:
    """Property tests for ResponseTransformer field mapping.

    **Feature: interface-modules-workflow-analysis, Property 9: ResponseTransformer Field Mapping**
    **Validates: Requirements 1.1**
    """

    @given(
        old_name=st.text(min_size=1, max_size=50),
        value=st.integers(min_value=0, max_value=10000),
        unchanged=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=100)
    def test_transformer_maps_fields(
        self, old_name: str, value: int, unchanged: str
    ) -> None:
        """BaseResponseTransformer SHALL map fields according to mapping."""
        assume(len(old_name.strip()) > 0 and len(unchanged.strip()) > 0)

        transformer = BaseResponseTransformer[SourceModel, TargetModel](
            target_type=TargetModel,
            field_mapping={"old_name": "new_name"},
        )

        source = SourceModel(old_name=old_name, value=value, unchanged=unchanged)
        target = transformer.transform(source)

        assert target.new_name == old_name
        assert target.value == value
        assert target.unchanged == unchanged

    @given(
        old_name=st.text(min_size=1, max_size=50),
        value=st.integers(min_value=0, max_value=10000),
        unchanged=st.text(min_size=1, max_size=50),
    )
    @settings(max_examples=100)
    def test_transformer_preserves_unmapped_fields(
        self, old_name: str, value: int, unchanged: str
    ) -> None:
        """BaseResponseTransformer SHALL preserve unmapped fields."""
        assume(len(old_name.strip()) > 0 and len(unchanged.strip()) > 0)

        transformer = BaseResponseTransformer[SourceModel, TargetModel](
            target_type=TargetModel,
            field_mapping={"old_name": "new_name"},
        )

        source = SourceModel(old_name=old_name, value=value, unchanged=unchanged)
        target = transformer.transform(source)

        assert target.unchanged == unchanged
        assert target.value == value

    def test_get_field_mapping_returns_copy(self) -> None:
        """get_field_mapping SHALL return a copy of the mapping."""
        mapping = {"old_name": "new_name"}
        transformer = BaseResponseTransformer[SourceModel, TargetModel](
            target_type=TargetModel,
            field_mapping=mapping,
        )

        result = transformer.get_field_mapping()
        assert result == mapping
        assert result is not mapping


# =============================================================================
# Property 10: VersionRouter Version Extraction
# =============================================================================


class TestVersionRouterVersionExtraction:
    """Property tests for VersionRouter version extraction.

    **Feature: interface-modules-workflow-analysis, Property 10: VersionRouter Version Extraction**
    **Validates: Requirements 1.2**
    """

    @given(version=version_str_strategy, default=version_str_strategy)
    @settings(max_examples=100)
    def test_version_router_default_version(
        self, version: str, default: str
    ) -> None:
        """VersionRouter SHALL use default version when header missing."""
        assume(len(default.strip()) > 0)
        router = VersionRouter(default_version=default)

        # Mock request without header
        class MockRequest:
            headers = {}

        request = MockRequest()
        extracted = router.get_version_from_request(request)

        assert extracted == default

    @given(
        version=version_str_strategy,
        header_name=st.text(
            alphabet=st.characters(whitelist_categories=("L",)),
            min_size=1,
            max_size=30,
        ),
    )
    @settings(max_examples=100)
    def test_version_router_extracts_from_header(
        self, version: str, header_name: str
    ) -> None:
        """VersionRouter SHALL extract version from specified header."""
        assume(len(version.strip()) > 0 and len(header_name.strip()) > 0)
        router = VersionRouter(header_name=header_name, default_version="1")

        class MockRequest:
            def __init__(self, headers: dict):
                self.headers = headers

        request = MockRequest({header_name: version})
        extracted = router.get_version_from_request(request)

        assert extracted == version

    @given(version=version_str_strategy)
    @settings(max_examples=100)
    def test_version_router_register_and_get(self, version: str) -> None:
        """VersionRouter SHALL register and retrieve routers by version."""
        assume(len(version.strip()) > 0)
        from fastapi import APIRouter

        router = VersionRouter()
        api_router = APIRouter()

        router.register_version(version, api_router)
        retrieved = router.get_router_for_version(version)

        assert retrieved is api_router

    def test_version_router_returns_none_for_unknown_version(self) -> None:
        """VersionRouter SHALL return None for unknown version."""
        router = VersionRouter()
        retrieved = router.get_router_for_version("unknown")

        assert retrieved is None


# =============================================================================
# Additional Tests
# =============================================================================


class TestVersionFormat:
    """Tests for VersionFormat enum."""

    def test_all_formats_defined(self) -> None:
        """VersionFormat SHALL define all expected formats."""
        expected = {"URL_PREFIX", "HEADER", "QUERY_PARAM", "ACCEPT_HEADER"}
        actual = {f.name for f in VersionFormat}
        assert actual == expected


class TestVersionConfig:
    """Tests for VersionConfig dataclass."""

    @given(version=version_int_strategy)
    @settings(max_examples=100)
    def test_version_config_defaults(self, version: int) -> None:
        """VersionConfig SHALL have sensible defaults."""
        config = VersionConfig[int](default_version=version)

        assert config.format == VersionFormat.URL_PREFIX
        assert config.header_name == "X-API-Version"
        assert config.query_param == "api_version"
        assert config.default_version == version
        assert config.supported_versions == []
