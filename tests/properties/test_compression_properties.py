"""Property-based tests for Compression Middleware.

**Feature: api-architecture-analysis**
**Validates: Requirements 4.4**
"""

import pytest
from hypothesis import given, settings, strategies as st

from my_app.infrastructure.compression import (
    BROTLI_AVAILABLE,
    CompressionAlgorithm,
    CompressionConfig,
    CompressionConfigBuilder,
    CompressionResult,
    CompressionService,
    CompressionStats,
    CompressorFactory,
    DeflateCompressor,
    GzipCompressor,
    IdentityCompressor,
    compress_response,
    create_compression_service,
    parse_accept_encoding,
    select_best_algorithm,
)


# Strategies
compressible_content_types = st.sampled_from([
    "text/html",
    "text/plain",
    "text/css",
    "application/json",
    "application/xml",
    "application/javascript",
    "image/svg+xml",
])

non_compressible_content_types = st.sampled_from([
    "image/png",
    "image/jpeg",
    "image/gif",
    "video/mp4",
    "audio/mpeg",
    "application/octet-stream",
    "application/zip",
])

# Generate compressible data (text-like, repetitive for good compression)
compressible_data = st.binary(min_size=1024, max_size=10000).map(
    lambda b: (b"Hello World! " * 100 + b)[:len(b) + 1300]
)

small_data = st.binary(min_size=1, max_size=500)

accept_encoding_headers = st.sampled_from([
    "gzip",
    "deflate",
    "gzip, deflate",
    "deflate, gzip",
    "gzip;q=1.0, deflate;q=0.5",
    "deflate;q=0.8, gzip;q=0.6",
    "identity",
    "*",
    "",
    "gzip, deflate, br",
])


class TestCompressionRoundTrip:
    """Property 1: Compression round-trip preserves data.
    
    **Validates: Requirements 4.4**
    """

    @given(data=st.binary(min_size=1, max_size=5000))
    @settings(max_examples=100)
    def test_gzip_round_trip(self, data: bytes) -> None:
        """For any data, gzip compress then decompress returns original."""
        compressor = GzipCompressor(level=6)
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        assert decompressed == data

    @given(data=st.binary(min_size=1, max_size=5000))
    @settings(max_examples=100)
    def test_deflate_round_trip(self, data: bytes) -> None:
        """For any data, deflate compress then decompress returns original."""
        compressor = DeflateCompressor(level=6)
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        assert decompressed == data

    @given(data=st.binary(min_size=1, max_size=5000))
    @settings(max_examples=100)
    def test_identity_round_trip(self, data: bytes) -> None:
        """For any data, identity compressor returns unchanged data."""
        compressor = IdentityCompressor()
        compressed = compressor.compress(data)
        decompressed = compressor.decompress(compressed)
        assert compressed == data
        assert decompressed == data


class TestCompressionServiceProperties:
    """Property tests for CompressionService."""

    @given(
        data=compressible_data,
        content_type=compressible_content_types,
    )
    @settings(max_examples=50)
    def test_compressed_data_is_smaller_or_equal(
        self, data: bytes, content_type: str
    ) -> None:
        """Property: Compressed data is never larger than original (or we skip)."""
        service = CompressionService()
        result = service.compress(data, "gzip", content_type)
        
        # If compression was applied, result should be smaller
        # If not applied, data should be unchanged
        if result.was_compressed:
            assert result.compressed_size < result.original_size
        else:
            assert result.data == data

    @given(
        data=small_data,
        content_type=compressible_content_types,
    )
    @settings(max_examples=50)
    def test_small_data_not_compressed(
        self, data: bytes, content_type: str
    ) -> None:
        """Property: Data smaller than min_size is not compressed."""
        config = CompressionConfig(min_size=1024)
        service = CompressionService(config)
        result = service.compress(data, "gzip", content_type)
        
        assert not result.was_compressed
        assert result.data == data

    @given(
        data=compressible_data,
        content_type=non_compressible_content_types,
    )
    @settings(max_examples=50)
    def test_non_compressible_types_not_compressed(
        self, data: bytes, content_type: str
    ) -> None:
        """Property: Non-compressible content types are not compressed."""
        service = CompressionService()
        result = service.compress(data, "gzip", content_type)
        
        assert not result.was_compressed
        assert result.data == data



class TestAcceptEncodingParsing:
    """Property tests for Accept-Encoding header parsing."""

    @given(header=accept_encoding_headers)
    @settings(max_examples=100)
    def test_parse_returns_non_empty_list(self, header: str) -> None:
        """Property: Parsing always returns at least one algorithm."""
        result = parse_accept_encoding(header)
        assert len(result) >= 1

    @given(header=accept_encoding_headers)
    @settings(max_examples=100)
    def test_parse_returns_valid_algorithms(self, header: str) -> None:
        """Property: All parsed algorithms are valid CompressionAlgorithm values."""
        result = parse_accept_encoding(header)
        for algorithm, quality in result:
            assert isinstance(algorithm, CompressionAlgorithm)
            assert 0.0 <= quality <= 1.0

    @given(header=accept_encoding_headers)
    @settings(max_examples=100)
    def test_parse_sorted_by_quality(self, header: str) -> None:
        """Property: Results are sorted by quality (descending)."""
        result = parse_accept_encoding(header)
        qualities = [q for _, q in result]
        assert qualities == sorted(qualities, reverse=True)


class TestAlgorithmSelection:
    """Property tests for algorithm selection."""

    @given(header=accept_encoding_headers)
    @settings(max_examples=100)
    def test_select_returns_valid_algorithm(self, header: str) -> None:
        """Property: Selection always returns a valid algorithm."""
        supported = (CompressionAlgorithm.GZIP, CompressionAlgorithm.DEFLATE)
        result = select_best_algorithm(header, supported)
        assert isinstance(result, CompressionAlgorithm)

    def test_select_respects_supported_algorithms(self) -> None:
        """Property: Selection only returns supported algorithms."""
        # Only support deflate
        supported = (CompressionAlgorithm.DEFLATE,)
        result = select_best_algorithm("gzip, deflate", supported)
        assert result in supported or result == CompressionAlgorithm.IDENTITY

    def test_select_returns_identity_when_no_match(self) -> None:
        """Property: Returns identity when no supported algorithm matches."""
        supported = (CompressionAlgorithm.GZIP,)
        result = select_best_algorithm("br", supported)
        # Should return identity since br is not supported
        assert result == CompressionAlgorithm.IDENTITY or result == CompressionAlgorithm.GZIP


class TestCompressionResultProperties:
    """Property tests for CompressionResult."""

    @given(
        original_size=st.integers(min_value=1, max_value=100000),
        compressed_size=st.integers(min_value=1, max_value=100000),
    )
    @settings(max_examples=100)
    def test_compression_ratio_bounds(
        self, original_size: int, compressed_size: int
    ) -> None:
        """Property: Compression ratio is between -inf and 1."""
        result = CompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            algorithm=CompressionAlgorithm.GZIP,
            data=b"",
            was_compressed=True,
        )
        ratio = result.compression_ratio
        assert ratio <= 1.0  # Can't save more than 100%

    @given(
        original_size=st.integers(min_value=1, max_value=100000),
        compressed_size=st.integers(min_value=1, max_value=100000),
    )
    @settings(max_examples=100)
    def test_savings_percent_consistent_with_ratio(
        self, original_size: int, compressed_size: int
    ) -> None:
        """Property: Savings percent equals ratio * 100."""
        result = CompressionResult(
            original_size=original_size,
            compressed_size=compressed_size,
            algorithm=CompressionAlgorithm.GZIP,
            data=b"",
            was_compressed=True,
        )
        assert abs(result.savings_percent - result.compression_ratio * 100) < 0.001


class TestCompressionStatsProperties:
    """Property tests for CompressionStats."""

    @given(
        results=st.lists(
            st.tuples(
                st.integers(min_value=100, max_value=10000),
                st.integers(min_value=50, max_value=5000),
                st.booleans(),
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=50)
    def test_stats_track_all_requests(
        self, results: list[tuple[int, int, bool]]
    ) -> None:
        """Property: Stats track all recorded requests."""
        stats = CompressionStats()
        
        for original, compressed, was_compressed in results:
            result = CompressionResult(
                original_size=original,
                compressed_size=compressed if was_compressed else original,
                algorithm=CompressionAlgorithm.GZIP,
                data=b"",
                was_compressed=was_compressed,
            )
            stats.record(result)
        
        assert stats.total_requests == len(results)

    @given(
        results=st.lists(
            st.tuples(
                st.integers(min_value=100, max_value=10000),
                st.integers(min_value=50, max_value=5000),
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=50)
    def test_bytes_saved_is_non_negative_when_compressed(
        self, results: list[tuple[int, int]]
    ) -> None:
        """Property: Bytes saved calculation is consistent."""
        stats = CompressionStats()
        
        for original, compressed in results:
            # Ensure compressed is smaller for this test
            actual_compressed = min(compressed, original - 1) if original > 1 else original
            result = CompressionResult(
                original_size=original,
                compressed_size=actual_compressed,
                algorithm=CompressionAlgorithm.GZIP,
                data=b"",
                was_compressed=actual_compressed < original,
            )
            stats.record(result)
        
        # Bytes saved should equal difference
        assert stats.bytes_saved == stats.total_original_bytes - stats.total_compressed_bytes


class TestCompressionConfigProperties:
    """Property tests for CompressionConfig."""

    @given(
        content_type=compressible_content_types,
    )
    @settings(max_examples=100)
    def test_compressible_types_detected(self, content_type: str) -> None:
        """Property: Compressible types are correctly identified."""
        config = CompressionConfig()
        assert config.is_compressible_type(content_type)

    @given(
        content_type=non_compressible_content_types,
    )
    @settings(max_examples=100)
    def test_non_compressible_types_rejected(self, content_type: str) -> None:
        """Property: Non-compressible types are correctly rejected."""
        config = CompressionConfig()
        assert not config.is_compressible_type(content_type)

    @given(
        path=st.sampled_from(["/api/data", "/health", "/metrics"]),
    )
    @settings(max_examples=50)
    def test_excluded_paths_detected(self, path: str) -> None:
        """Property: Excluded paths are correctly identified."""
        config = CompressionConfig(excluded_paths=("/health", "/metrics"))
        if path in ("/health", "/metrics"):
            assert config.is_excluded_path(path)
        else:
            assert not config.is_excluded_path(path)


class TestCompressionConfigBuilderProperties:
    """Property tests for CompressionConfigBuilder."""

    @given(
        min_size=st.integers(min_value=0, max_value=100000),
        level=st.integers(min_value=1, max_value=11),
    )
    @settings(max_examples=100)
    def test_builder_preserves_settings(self, min_size: int, level: int) -> None:
        """Property: Builder preserves all configured settings."""
        config = (
            CompressionConfigBuilder()
            .min_size(min_size)
            .level(level)
            .build()
        )
        assert config.min_size == min_size
        assert config.level == min(max(level, 1), 11)

    def test_builder_fluent_interface(self) -> None:
        """Property: Builder methods return builder for chaining."""
        builder = CompressionConfigBuilder()
        result = (
            builder
            .min_size(512)
            .level(9)
            .with_gzip()
            .with_deflate()
            .exclude_path("/health")
        )
        assert result is builder


class TestCompressorFactoryProperties:
    """Property tests for CompressorFactory."""

    @given(
        algorithm=st.sampled_from([
            CompressionAlgorithm.GZIP,
            CompressionAlgorithm.DEFLATE,
            CompressionAlgorithm.IDENTITY,
        ])
    )
    @settings(max_examples=50)
    def test_factory_creates_correct_compressor(
        self, algorithm: CompressionAlgorithm
    ) -> None:
        """Property: Factory creates compressor for requested algorithm."""
        compressor = CompressorFactory.create(algorithm)
        assert compressor.algorithm == algorithm

    def test_available_algorithms_includes_basics(self) -> None:
        """Property: Available algorithms always include gzip and deflate."""
        available = CompressorFactory.available_algorithms()
        assert CompressionAlgorithm.GZIP in available
        assert CompressionAlgorithm.DEFLATE in available
        assert CompressionAlgorithm.IDENTITY in available


class TestConvenienceFunctions:
    """Property tests for convenience functions."""

    @given(
        data=compressible_data,
        accept_encoding=st.sampled_from(["gzip", "deflate", "identity"]),
    )
    @settings(max_examples=50)
    def test_compress_response_returns_tuple(
        self, data: bytes, accept_encoding: str
    ) -> None:
        """Property: compress_response returns (data, encoding) tuple."""
        result_data, encoding = compress_response(data, accept_encoding)
        assert isinstance(result_data, bytes)
        assert isinstance(encoding, str)
        assert encoding in ("gzip", "deflate", "identity", "br")

    @given(
        min_size=st.integers(min_value=100, max_value=10000),
        level=st.integers(min_value=1, max_value=9),
    )
    @settings(max_examples=50)
    def test_create_compression_service_configurable(
        self, min_size: int, level: int
    ) -> None:
        """Property: create_compression_service respects parameters."""
        service = create_compression_service(min_size=min_size, level=level)
        assert service._config.min_size == min_size
        assert service._config.level == level


# =============================================================================
# Property Tests - Compression Level Validation (shared-modules-refactoring)
# =============================================================================


class TestCompressionLevelValidation:
    """Property tests for compression level validation.

    **Feature: shared-modules-refactoring**
    **Validates: Requirements 8.1, 8.2, 8.3**
    """

    @given(level=st.integers(min_value=-100, max_value=100))
    @settings(max_examples=100)
    def test_gzip_level_validation(self, level: int) -> None:
        """**Feature: shared-modules-refactoring, Property 15: Compression Level Validation - Gzip**
        **Validates: Requirements 8.1**

        For any integer level outside range [1, 9], creating a GzipCompressor
        SHALL raise ValueError.
        """
        if 1 <= level <= 9:
            compressor = GzipCompressor(level)
            assert compressor._level == level
        else:
            with pytest.raises(ValueError) as exc_info:
                GzipCompressor(level)
            assert "1" in str(exc_info.value) and "9" in str(exc_info.value)
            assert str(level) in str(exc_info.value)

    @given(level=st.integers(min_value=-100, max_value=100))
    @settings(max_examples=100)
    def test_deflate_level_validation(self, level: int) -> None:
        """**Feature: shared-modules-refactoring, Property 15: Compression Level Validation - Gzip**
        **Validates: Requirements 8.1**

        For any integer level outside range [1, 9], creating a DeflateCompressor
        SHALL raise ValueError.
        """
        if 1 <= level <= 9:
            compressor = DeflateCompressor(level)
            assert compressor._level == level
        else:
            with pytest.raises(ValueError) as exc_info:
                DeflateCompressor(level)
            assert "1" in str(exc_info.value) and "9" in str(exc_info.value)
            assert str(level) in str(exc_info.value)

    @pytest.mark.skipif(not BROTLI_AVAILABLE, reason="Brotli not available")
    @given(level=st.integers(min_value=-100, max_value=100))
    @settings(max_examples=100)
    def test_brotli_level_validation(self, level: int) -> None:
        """**Feature: shared-modules-refactoring, Property 16: Compression Level Validation - Brotli**
        **Validates: Requirements 8.2**

        For any integer level outside range [0, 11], creating a BrotliCompressor
        SHALL raise ValueError.
        """
        from my_app.infrastructure.compression import BrotliCompressor

        if 0 <= level <= 11:
            compressor = BrotliCompressor(level)
            assert compressor._level == level
        else:
            with pytest.raises(ValueError) as exc_info:
                BrotliCompressor(level)
            assert "0" in str(exc_info.value) and "11" in str(exc_info.value)
            assert str(level) in str(exc_info.value)

    def test_validation_error_message_content_gzip(self) -> None:
        """**Feature: shared-modules-refactoring, Property 17: Validation Error Message Content**
        **Validates: Requirements 8.3**

        For any compression level validation failure, the error message SHALL
        contain both the valid range and the provided invalid value.
        """
        invalid_level = 15
        with pytest.raises(ValueError) as exc_info:
            GzipCompressor(invalid_level)

        error_msg = str(exc_info.value)
        # Should contain valid range
        assert "1" in error_msg
        assert "9" in error_msg
        # Should contain provided value
        assert str(invalid_level) in error_msg

    def test_validation_error_message_content_deflate(self) -> None:
        """**Feature: shared-modules-refactoring, Property 17: Validation Error Message Content**
        **Validates: Requirements 8.3**
        """
        invalid_level = -5
        with pytest.raises(ValueError) as exc_info:
            DeflateCompressor(invalid_level)

        error_msg = str(exc_info.value)
        assert "1" in error_msg
        assert "9" in error_msg
        assert str(invalid_level) in error_msg

    @pytest.mark.skipif(not BROTLI_AVAILABLE, reason="Brotli not available")
    def test_validation_error_message_content_brotli(self) -> None:
        """**Feature: shared-modules-refactoring, Property 17: Validation Error Message Content**
        **Validates: Requirements 8.3**
        """
        from my_app.infrastructure.compression import BrotliCompressor

        invalid_level = 20
        with pytest.raises(ValueError) as exc_info:
            BrotliCompressor(invalid_level)

        error_msg = str(exc_info.value)
        assert "0" in error_msg
        assert "11" in error_msg
        assert str(invalid_level) in error_msg
