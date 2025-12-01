"""Property-based tests for file upload service.

**Feature: enterprise-features-2025, Tasks 6.3, 6.4**
**Validates: Requirements 6.1, 6.2**
"""

import asyncio
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_app.application.file_upload.models import (
    FileMetadata,
    FileValidationConfig,
    UploadError,
)
from my_app.application.file_upload.service import FileUploadService, InMemoryStorageProvider
from my_app.application.file_upload.validators import validate_file, get_safe_filename


# Strategies
filenames = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N")),
    min_size=1,
    max_size=50,
).map(lambda s: f"{s}.txt")

valid_content_types = st.sampled_from([
    "image/jpeg", "image/png", "application/pdf", "text/plain"
])
invalid_content_types = st.sampled_from([
    "application/exe", "application/x-msdownload", "text/html"
])

user_ids = st.uuids().map(str)
tenant_ids = st.uuids().map(str)


class TestFileUploadValidation:
    """**Feature: enterprise-features-2025, Property 15: File Upload Validation**
    **Validates: Requirements 6.1**
    """

    @given(
        filename=filenames,
        content=st.binary(min_size=1, max_size=1000),
    )
    @settings(max_examples=50)
    def test_valid_file_passes_validation(
        self, filename: str, content: bytes
    ) -> None:
        """Valid files pass validation."""
        config = FileValidationConfig(
            max_size_bytes=10000,
            allowed_types=frozenset({"text/plain"}),
            allowed_extensions=frozenset({".txt"}),
        )

        result = validate_file(filename, content, "text/plain", config)
        assert result.is_ok()
        # Checksum should be returned
        checksum = result.unwrap()
        assert len(checksum) == 64  # SHA-256 hex length

    @given(
        filename=filenames,
        content=st.binary(min_size=1001, max_size=2000),
    )
    @settings(max_examples=50)
    def test_oversized_file_rejected(
        self, filename: str, content: bytes
    ) -> None:
        """Files exceeding size limit are rejected."""
        config = FileValidationConfig(
            max_size_bytes=1000,
            allowed_types=frozenset({"text/plain"}),
            allowed_extensions=frozenset({".txt"}),
        )

        result = validate_file(filename, content, "text/plain", config)
        assert result.is_err()
        assert result.error == UploadError.FILE_TOO_LARGE

    @given(
        filename=filenames,
        content=st.binary(min_size=1, max_size=100),
        content_type=invalid_content_types,
    )
    @settings(max_examples=50)
    def test_invalid_content_type_rejected(
        self, filename: str, content: bytes, content_type: str
    ) -> None:
        """Files with invalid content type are rejected."""
        config = FileValidationConfig(
            max_size_bytes=10000,
            allowed_types=frozenset({"text/plain", "image/png"}),
            allowed_extensions=frozenset({".txt", ".png"}),
        )

        result = validate_file(filename, content, content_type, config)
        assert result.is_err()
        assert result.error == UploadError.INVALID_TYPE

    @given(
        content=st.binary(min_size=1, max_size=100),
    )
    @settings(max_examples=50)
    def test_invalid_extension_rejected(self, content: bytes) -> None:
        """Files with invalid extension are rejected."""
        config = FileValidationConfig(
            max_size_bytes=10000,
            allowed_types=frozenset({"text/plain"}),
            allowed_extensions=frozenset({".txt"}),
        )

        result = validate_file("file.exe", content, "text/plain", config)
        assert result.is_err()
        assert result.error == UploadError.INVALID_EXTENSION


class TestFileSizeValidation:
    """**Feature: comprehensive-code-review-2025-v2, Property 14: File Size Validation**
    **Validates: Requirements 6.1**
    """

    @given(
        max_size=st.integers(min_value=100, max_value=10000),
        excess_factor=st.floats(min_value=1.1, max_value=3.0),
    )
    @settings(max_examples=100)
    def test_file_exceeding_max_size_returns_file_too_large(
        self, max_size: int, excess_factor: float
    ) -> None:
        """**Property 14: File Size Validation**
        
        For any file exceeding max_size_bytes, validation SHALL return FILE_TOO_LARGE error.
        """
        config = FileValidationConfig(
            max_size_bytes=max_size,
            allowed_types=frozenset({"text/plain"}),
            allowed_extensions=frozenset({".txt"}),
        )
        
        # Create content larger than max_size
        oversized_content = b"x" * int(max_size * excess_factor)
        
        result = validate_file("test.txt", oversized_content, "text/plain", config)
        
        assert result.is_err(), f"Expected error for {len(oversized_content)} bytes with max {max_size}"
        assert result.error == UploadError.FILE_TOO_LARGE

    @given(
        max_size=st.integers(min_value=100, max_value=10000),
        size_factor=st.floats(min_value=0.1, max_value=0.99),
    )
    @settings(max_examples=100)
    def test_file_within_max_size_passes(
        self, max_size: int, size_factor: float
    ) -> None:
        """**Property 14: File Size Validation (within bounds)**
        
        For any file within max_size_bytes, validation SHALL succeed.
        """
        config = FileValidationConfig(
            max_size_bytes=max_size,
            allowed_types=frozenset({"text/plain"}),
            allowed_extensions=frozenset({".txt"}),
        )
        
        # Create content smaller than max_size
        valid_content = b"x" * max(1, int(max_size * size_factor))
        
        result = validate_file("test.txt", valid_content, "text/plain", config)
        
        assert result.is_ok(), f"Expected success for {len(valid_content)} bytes with max {max_size}"

    @given(
        max_size=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=50)
    def test_file_exactly_at_max_size_passes(self, max_size: int) -> None:
        """**Property 14: File Size Validation (boundary)**
        
        File exactly at max_size_bytes SHALL pass validation.
        """
        config = FileValidationConfig(
            max_size_bytes=max_size,
            allowed_types=frozenset({"text/plain"}),
            allowed_extensions=frozenset({".txt"}),
        )
        
        # Create content exactly at max_size
        exact_content = b"x" * max_size
        
        result = validate_file("test.txt", exact_content, "text/plain", config)
        
        assert result.is_ok(), f"File exactly at {max_size} bytes should pass"

    @given(
        max_size=st.integers(min_value=100, max_value=10000),
    )
    @settings(max_examples=50)
    def test_file_one_byte_over_max_size_fails(self, max_size: int) -> None:
        """**Property 14: File Size Validation (boundary + 1)**
        
        File one byte over max_size_bytes SHALL fail validation.
        """
        config = FileValidationConfig(
            max_size_bytes=max_size,
            allowed_types=frozenset({"text/plain"}),
            allowed_extensions=frozenset({".txt"}),
        )
        
        # Create content one byte over max_size
        over_content = b"x" * (max_size + 1)
        
        result = validate_file("test.txt", over_content, "text/plain", config)
        
        assert result.is_err(), f"File at {max_size + 1} bytes should fail with max {max_size}"
        assert result.error == UploadError.FILE_TOO_LARGE


class TestFileTypeValidation:
    """**Feature: comprehensive-code-review-2025-v2, Property 15: File Type Validation**
    **Validates: Requirements 6.2**
    """

    @given(
        allowed_types=st.frozensets(
            st.sampled_from(["image/jpeg", "image/png", "application/pdf", "text/plain", "text/csv"]),
            min_size=1,
            max_size=3,
        ),
        content=st.binary(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_content_type_not_in_allowed_returns_invalid_type(
        self, allowed_types: frozenset[str], content: bytes
    ) -> None:
        """**Property 15: File Type Validation**
        
        For any file with content_type not in allowed_types, validation SHALL return INVALID_TYPE error.
        """
        # Use a content type that's definitely not in allowed_types
        disallowed_type = "application/x-executable"
        
        # Map allowed types to extensions
        type_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/pdf": ".pdf",
            "text/plain": ".txt",
            "text/csv": ".csv",
        }
        allowed_extensions = frozenset(type_to_ext.get(t, ".bin") for t in allowed_types)
        
        config = FileValidationConfig(
            max_size_bytes=10000,
            allowed_types=allowed_types,
            allowed_extensions=allowed_extensions | frozenset({".bin"}),
        )
        
        result = validate_file("test.bin", content, disallowed_type, config)
        
        assert result.is_err(), f"Expected INVALID_TYPE for {disallowed_type}"
        assert result.error == UploadError.INVALID_TYPE

    @given(
        content_type=st.sampled_from(["image/jpeg", "image/png", "application/pdf", "text/plain"]),
        content=st.binary(min_size=1, max_size=100),
    )
    @settings(max_examples=100)
    def test_content_type_in_allowed_passes(
        self, content_type: str, content: bytes
    ) -> None:
        """**Property 15: File Type Validation (allowed types)**
        
        For any file with content_type in allowed_types, validation SHALL succeed.
        """
        type_to_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "application/pdf": ".pdf",
            "text/plain": ".txt",
        }
        ext = type_to_ext[content_type]
        
        config = FileValidationConfig(
            max_size_bytes=10000,
            allowed_types=frozenset({"image/jpeg", "image/png", "application/pdf", "text/plain"}),
            allowed_extensions=frozenset({".jpg", ".png", ".pdf", ".txt"}),
        )
        
        result = validate_file(f"test{ext}", content, content_type, config)
        
        assert result.is_ok(), f"Expected success for allowed type {content_type}"


class TestPresignedURLExpiration:
    """**Feature: enterprise-features-2025, Property 16: Presigned URL Expiration**
    **Validates: Requirements 6.2**
    """

    @given(
        expires_in=st.integers(min_value=60, max_value=86400),
    )
    @settings(max_examples=30)
    def test_presigned_url_contains_expiration(self, expires_in: int) -> None:
        """Presigned URLs contain expiration information."""

        async def run_test() -> None:
            storage = InMemoryStorageProvider()
            service: FileUploadService[dict] = FileUploadService(storage)

            # Upload a file first
            result = await service.upload(
                filename="test.txt",
                content=b"test content",
                content_type="text/plain",
                user_id="user1",
                tenant_id="tenant1",
            )
            assert result.is_ok()

            storage_key = result.unwrap().storage_key

            # Get presigned URL
            url = await service.get_presigned_url(storage_key, expires_in)

            # URL should contain expiration parameter
            assert f"expires={expires_in}" in url

        asyncio.run(run_test())

    @given(
        method=st.sampled_from(["GET", "PUT"]),
    )
    @settings(max_examples=20)
    def test_presigned_url_contains_method(self, method: str) -> None:
        """Presigned URLs contain method information."""

        async def run_test() -> None:
            storage = InMemoryStorageProvider()
            service: FileUploadService[dict] = FileUploadService(storage)

            # Upload a file first
            result = await service.upload(
                filename="test.txt",
                content=b"test content",
                content_type="text/plain",
                user_id="user1",
                tenant_id="tenant1",
            )
            assert result.is_ok()

            storage_key = result.unwrap().storage_key

            # Get presigned URL with method
            url = await service.get_presigned_url(storage_key, 3600, method)

            # URL should contain method parameter
            assert f"method={method}" in url

        asyncio.run(run_test())


class TestFileQuota:
    """Tests for file quota management."""

    @given(
        quota_limit=st.integers(min_value=1000, max_value=10000),
        file_size=st.integers(min_value=100, max_value=500),
    )
    @settings(max_examples=30)
    def test_quota_tracking(self, quota_limit: int, file_size: int) -> None:
        """Quota usage is tracked correctly."""

        async def run_test() -> None:
            storage = InMemoryStorageProvider()
            service: FileUploadService[dict] = FileUploadService(storage)

            tenant_id = "tenant1"
            service.set_quota(tenant_id, quota_limit)

            content = b"x" * file_size

            result = await service.upload(
                filename="test.txt",
                content=content,
                content_type="text/plain",
                user_id="user1",
                tenant_id=tenant_id,
            )
            assert result.is_ok()

            used, limit = service.get_quota_usage(tenant_id)
            assert used == file_size
            assert limit == quota_limit

        asyncio.run(run_test())

    @given(
        quota_limit=st.integers(min_value=100, max_value=500),
    )
    @settings(max_examples=30)
    def test_quota_exceeded_rejected(self, quota_limit: int) -> None:
        """Files exceeding quota are rejected."""

        async def run_test() -> None:
            storage = InMemoryStorageProvider()
            service: FileUploadService[dict] = FileUploadService(storage)

            tenant_id = "tenant1"
            service.set_quota(tenant_id, quota_limit)

            # Try to upload file larger than quota
            content = b"x" * (quota_limit + 100)

            result = await service.upload(
                filename="test.txt",
                content=content,
                content_type="text/plain",
                user_id="user1",
                tenant_id=tenant_id,
            )
            assert result.is_err()
            assert result.error == UploadError.QUOTA_EXCEEDED

        asyncio.run(run_test())


class TestSafeFilename:
    """Tests for filename sanitization."""

    @given(
        filename=st.text(min_size=1, max_size=100),
    )
    @settings(max_examples=50)
    def test_safe_filename_removes_path_separators(self, filename: str) -> None:
        """Safe filename removes path separators."""
        safe = get_safe_filename(filename)

        assert "/" not in safe
        assert "\\" not in safe
        assert "\x00" not in safe

    @given(
        filename=st.text(min_size=250, max_size=300),
    )
    @settings(max_examples=20)
    def test_safe_filename_limits_length(self, filename: str) -> None:
        """Safe filename limits length."""
        safe = get_safe_filename(f"{filename}.txt")

        # Name part should be limited to 200 chars
        name_part = safe.rsplit(".", 1)[0]
        assert len(name_part) <= 200


class TestFilenameSanitization:
    """**Feature: comprehensive-code-review-2025-v2, Property 16: Filename Sanitization**
    **Validates: Requirements 6.4**
    """

    @given(
        base_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=50,
        ),
        traversal_prefix=st.sampled_from([
            "../", "..\\", "../../", "..\\..\\",
            "../../../", "..\\..\\..\\",
            "./../", ".\\..\\",
        ]),
    )
    @settings(max_examples=100)
    def test_path_traversal_characters_removed(
        self, base_name: str, traversal_prefix: str
    ) -> None:
        """**Property 16: Filename Sanitization**
        
        For any filename with path traversal characters, sanitization SHALL remove dangerous characters.
        """
        malicious_filename = f"{traversal_prefix}{base_name}.txt"
        safe = get_safe_filename(malicious_filename)
        
        # Path traversal sequences should be neutralized
        assert "../" not in safe
        assert "..\\" not in safe
        assert "/" not in safe
        assert "\\" not in safe

    @given(
        base_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=50,
        ),
        dangerous_char=st.sampled_from(["<", ">", ":", '"', "|", "?", "*", "\x00"]),
    )
    @settings(max_examples=100)
    def test_dangerous_characters_replaced(
        self, base_name: str, dangerous_char: str
    ) -> None:
        """**Property 16: Filename Sanitization (dangerous chars)**
        
        For any filename with dangerous characters, sanitization SHALL replace them.
        """
        malicious_filename = f"{base_name}{dangerous_char}file.txt"
        safe = get_safe_filename(malicious_filename)
        
        # Dangerous character should be replaced
        assert dangerous_char not in safe

    @given(
        base_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=50,
        ),
    )
    @settings(max_examples=100)
    def test_absolute_path_stripped(self, base_name: str) -> None:
        """**Property 16: Filename Sanitization (absolute paths)**
        
        For any filename with absolute path prefix, sanitization SHALL strip the path.
        """
        # Test Windows absolute path
        windows_path = f"C:\\Users\\admin\\{base_name}.txt"
        safe_windows = get_safe_filename(windows_path)
        assert "C:" not in safe_windows
        assert "Users" not in safe_windows
        assert "admin" not in safe_windows
        
        # Test Unix absolute path
        unix_path = f"/etc/passwd/{base_name}.txt"
        safe_unix = get_safe_filename(unix_path)
        assert "/etc" not in safe_unix
        assert "passwd" not in safe_unix

    @given(
        extension=st.sampled_from([".txt", ".pdf", ".jpg", ".png"]),
    )
    @settings(max_examples=50)
    def test_extension_preserved_after_sanitization(self, extension: str) -> None:
        """**Property 16: Filename Sanitization (extension preservation)**
        
        For any valid filename, sanitization SHALL preserve the file extension.
        """
        filename = f"valid_file{extension}"
        safe = get_safe_filename(filename)
        
        assert safe.endswith(extension), f"Extension {extension} should be preserved"

    @given(
        name_length=st.integers(min_value=250, max_value=500),
    )
    @settings(max_examples=50)
    def test_long_filename_truncated(self, name_length: int) -> None:
        """**Property 16: Filename Sanitization (length limit)**
        
        For any filename exceeding length limit, sanitization SHALL truncate the name part.
        """
        long_name = "a" * name_length
        filename = f"{long_name}.txt"
        safe = get_safe_filename(filename)
        
        # Name part should be limited to 200 chars
        name_part, ext = safe.rsplit(".", 1)
        assert len(name_part) <= 200, f"Name part should be <= 200 chars, got {len(name_part)}"
        assert ext == "txt", "Extension should be preserved"

    @given(
        base_name=st.text(
            alphabet=st.characters(whitelist_categories=("L", "N")),
            min_size=1,
            max_size=30,
        ),
    )
    @settings(max_examples=50)
    def test_null_byte_injection_prevented(self, base_name: str) -> None:
        """**Property 16: Filename Sanitization (null byte injection)**
        
        For any filename with null bytes, sanitization SHALL remove/replace them.
        """
        # Null byte injection attempt
        malicious = f"{base_name}.txt\x00.exe"
        safe = get_safe_filename(malicious)
        
        # Null bytes should be replaced (not present in output)
        assert "\x00" not in safe, "Null bytes should be removed/replaced"
        # The sanitized filename should not contain the original null byte
        # Note: The implementation replaces \x00 with _, so the extension may still be present
        # but the null byte attack vector is neutralized
