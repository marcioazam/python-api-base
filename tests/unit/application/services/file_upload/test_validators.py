"""Unit tests for file upload validators.

**Feature: test-coverage-90-percent**
"""

import io
import pytest

from application.services.file_upload.models import FileValidationConfig, UploadError
from application.services.file_upload.validators.validators import (
    validate_file,
    validate_file_stream,
    validate_magic_bytes,
    get_safe_filename,
)


@pytest.fixture
def config() -> FileValidationConfig:
    """Create validation config."""
    return FileValidationConfig(
        max_size_bytes=1024 * 1024,  # 1MB
        allowed_types=frozenset({"image/jpeg", "image/png", "application/pdf", "text/plain"}),
        allowed_extensions=frozenset({".jpg", ".jpeg", ".png", ".pdf", ".txt"}),
    )


class TestValidateMagicBytes:
    """Tests for validate_magic_bytes function."""

    def test_valid_jpeg(self) -> None:
        """Should validate JPEG magic bytes."""
        content = b"\xff\xd8\xff" + b"rest of jpeg"
        assert validate_magic_bytes(content, "image/jpeg") is True

    def test_invalid_jpeg(self) -> None:
        """Should reject invalid JPEG magic bytes."""
        content = b"not a jpeg"
        assert validate_magic_bytes(content, "image/jpeg") is False

    def test_valid_png(self) -> None:
        """Should validate PNG magic bytes."""
        content = b"\x89PNG\r\n\x1a\n" + b"rest of png"
        assert validate_magic_bytes(content, "image/png") is True

    def test_invalid_png(self) -> None:
        """Should reject invalid PNG magic bytes."""
        content = b"not a png"
        assert validate_magic_bytes(content, "image/png") is False

    def test_valid_pdf(self) -> None:
        """Should validate PDF magic bytes."""
        content = b"%PDF-1.4" + b"rest of pdf"
        assert validate_magic_bytes(content, "application/pdf") is True

    def test_valid_gif87a(self) -> None:
        """Should validate GIF87a magic bytes."""
        content = b"GIF87a" + b"rest of gif"
        assert validate_magic_bytes(content, "image/gif") is True

    def test_valid_gif89a(self) -> None:
        """Should validate GIF89a magic bytes."""
        content = b"GIF89a" + b"rest of gif"
        assert validate_magic_bytes(content, "image/gif") is True

    def test_valid_webp(self) -> None:
        """Should validate WebP magic bytes."""
        content = b"RIFF" + b"\x00\x00\x00\x00" + b"WEBP" + b"rest"
        assert validate_magic_bytes(content, "image/webp") is True

    def test_invalid_webp_missing_webp_signature(self) -> None:
        """Should reject WebP without WEBP signature."""
        content = b"RIFF" + b"\x00\x00\x00\x00" + b"XXXX"
        assert validate_magic_bytes(content, "image/webp") is False

    def test_unknown_type_passes(self) -> None:
        """Should pass unknown content types (no signature to validate)."""
        content = b"any content"
        assert validate_magic_bytes(content, "text/plain") is True

    def test_valid_zip(self) -> None:
        """Should validate ZIP magic bytes."""
        content = b"PK\x03\x04" + b"rest of zip"
        assert validate_magic_bytes(content, "application/zip") is True

    def test_valid_gzip(self) -> None:
        """Should validate GZIP magic bytes."""
        content = b"\x1f\x8b" + b"rest of gzip"
        assert validate_magic_bytes(content, "application/gzip") is True


class TestValidateFile:
    """Tests for validate_file function."""

    def test_valid_file(self, config: FileValidationConfig) -> None:
        """Should validate valid file."""
        content = b"plain text content"
        result = validate_file("test.txt", content, "text/plain", config)

        assert result.is_ok()
        checksum = result.unwrap()
        assert len(checksum) == 64  # SHA-256 hex

    def test_file_too_large(self, config: FileValidationConfig) -> None:
        """Should reject file exceeding size limit."""
        content = b"x" * (config.max_size_bytes + 1)
        result = validate_file("test.txt", content, "text/plain", config)

        assert result.is_err()
        assert result.error == UploadError.FILE_TOO_LARGE

    def test_invalid_content_type(self, config: FileValidationConfig) -> None:
        """Should reject invalid content type."""
        content = b"content"
        result = validate_file("test.exe", content, "application/octet-stream", config)

        assert result.is_err()
        assert result.error == UploadError.INVALID_TYPE

    def test_invalid_extension(self, config: FileValidationConfig) -> None:
        """Should reject invalid extension."""
        content = b"content"
        result = validate_file("test.exe", content, "text/plain", config)

        assert result.is_err()
        assert result.error == UploadError.INVALID_EXTENSION

    def test_magic_bytes_mismatch(self, config: FileValidationConfig) -> None:
        """Should reject file with mismatched magic bytes."""
        content = b"not a jpeg"  # Invalid JPEG magic bytes
        result = validate_file("test.jpg", content, "image/jpeg", config)

        assert result.is_err()
        assert result.error == UploadError.INVALID_TYPE

    def test_valid_jpeg_with_magic_bytes(self, config: FileValidationConfig) -> None:
        """Should validate JPEG with correct magic bytes."""
        content = b"\xff\xd8\xff" + b"rest of jpeg content"
        result = validate_file("photo.jpg", content, "image/jpeg", config)

        assert result.is_ok()


class TestValidateFileStream:
    """Tests for validate_file_stream function."""

    def test_valid_stream(self, config: FileValidationConfig) -> None:
        """Should validate valid file stream."""
        content = b"plain text content"
        stream = io.BytesIO(content)

        result = validate_file_stream("test.txt", stream, "text/plain", config)

        assert result.is_ok()
        file_content, checksum = result.unwrap()
        assert file_content == content
        assert len(checksum) == 64

    def test_invalid_content_type_stream(self, config: FileValidationConfig) -> None:
        """Should reject stream with invalid content type."""
        stream = io.BytesIO(b"content")

        result = validate_file_stream("test.exe", stream, "application/octet-stream", config)

        assert result.is_err()
        assert result.error == UploadError.INVALID_TYPE

    def test_invalid_extension_stream(self, config: FileValidationConfig) -> None:
        """Should reject stream with invalid extension."""
        stream = io.BytesIO(b"content")

        result = validate_file_stream("test.exe", stream, "text/plain", config)

        assert result.is_err()
        assert result.error == UploadError.INVALID_EXTENSION

    def test_stream_too_large(self, config: FileValidationConfig) -> None:
        """Should reject stream exceeding size limit."""
        content = b"x" * (config.max_size_bytes + 1)
        stream = io.BytesIO(content)

        result = validate_file_stream("test.txt", stream, "text/plain", config)

        assert result.is_err()
        assert result.error == UploadError.FILE_TOO_LARGE


class TestGetSafeFilename:
    """Tests for get_safe_filename function."""

    def test_simple_filename(self) -> None:
        """Should keep simple filename unchanged."""
        assert get_safe_filename("document.pdf") == "document.pdf"

    def test_path_traversal_unix(self) -> None:
        """Should remove path traversal attempts (Unix)."""
        assert get_safe_filename("../../../etc/passwd") == "passwd"

    def test_path_traversal_windows(self) -> None:
        """Should remove path traversal attempts (Windows)."""
        assert get_safe_filename("..\\..\\windows\\system32\\config") == "config"

    def test_dangerous_characters(self) -> None:
        """Should replace dangerous characters."""
        result = get_safe_filename("file<script>.txt")
        assert "<" not in result
        assert ">" not in result
        assert result == "file_script_.txt"

    def test_null_byte(self) -> None:
        """Should remove null bytes."""
        result = get_safe_filename("file\x00.txt")
        assert "\x00" not in result

    def test_long_filename(self) -> None:
        """Should truncate long filenames."""
        long_name = "a" * 300 + ".pdf"
        result = get_safe_filename(long_name)
        assert len(result) <= 204  # 200 chars + ".pdf"
        assert result.endswith(".pdf")

    def test_special_characters(self) -> None:
        """Should replace special characters."""
        result = get_safe_filename('file:name|test?.txt')
        assert ":" not in result
        assert "|" not in result
        assert "?" not in result

    def test_quotes(self) -> None:
        """Should replace quotes."""
        result = get_safe_filename('file"name.txt')
        assert '"' not in result
