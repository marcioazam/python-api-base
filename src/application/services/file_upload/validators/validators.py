"""File validation utilities for secure file uploads.

This module provides comprehensive file validation including size limits,
content type verification, extension validation, and filename sanitization.

Security Features:
    - File size validation to prevent DoS attacks
    - Content type whitelist validation
    - File extension validation
    - Magic bytes validation to prevent content-type spoofing
    - Path traversal prevention in filenames
    - Dangerous character sanitization
    - SHA-256 checksum calculation for integrity verification

**Feature: enterprise-features-2025, Task 6.1: File validation**
**Validates: Requirements 6.1**

Example:
    >>> from application.file_upload.models import FileValidationConfig
    >>> config = FileValidationConfig(max_size_bytes=1024 * 1024)
    >>> result = validate_file("document.pdf", content, "application/pdf", config)
    >>> if result.is_ok():
    ...     checksum = result.unwrap()
"""

import hashlib
from pathlib import PurePath
from typing import BinaryIO, Final

from application.services.file_upload.models import (
    FileValidationConfig,
    UploadError,
)
from core.base.patterns.result import Err, Ok, Result

# =============================================================================
# Magic Bytes Signatures for Content-Type Validation
# =============================================================================

MAGIC_BYTES: Final[dict[str, list[bytes]]] = {
    # Images
    "image/jpeg": [b"\xff\xd8\xff"],
    "image/png": [b"\x89PNG\r\n\x1a\n"],
    "image/gif": [b"GIF87a", b"GIF89a"],
    "image/webp": [b"RIFF"],  # RIFF followed by WEBP
    # Documents
    "application/pdf": [b"%PDF"],
    # Archives
    "application/zip": [b"PK\x03\x04", b"PK\x05\x06"],
    "application/gzip": [b"\x1f\x8b"],
}

# Secondary validation for formats with complex signatures
WEBP_SIGNATURE: Final[bytes] = b"WEBP"


def validate_magic_bytes(content: bytes, content_type: str) -> bool:
    """Validate file content matches declared content type via magic bytes.

    Prevents content-type spoofing attacks where malicious files are
    disguised as safe file types.

    Args:
        content: File content as bytes.
        content_type: Declared MIME type to validate against.

    Returns:
        True if content matches declared type or no signature exists.

    Example:
        >>> validate_magic_bytes(b"\xff\xd8\xff...", "image/jpeg")
        True
        >>> validate_magic_bytes(b"malicious", "image/jpeg")
        False
    """
    signatures = MAGIC_BYTES.get(content_type)
    if signatures is None:
        # No signature to validate - allow (text files, csv, etc.)
        return True

    # Check primary signature
    if not any(content.startswith(sig) for sig in signatures):
        return False

    # Additional validation for WebP (RIFF + WEBP)
    if content_type == "image/webp":
        return len(content) >= 12 and content[8:12] == WEBP_SIGNATURE

    return True


def validate_file(
    filename: str,
    content: bytes,
    content_type: str,
    config: FileValidationConfig,
) -> Result[str, UploadError]:
    """Validate a file against configuration rules.

    Performs comprehensive validation including size, content type, and extension
    checks. Returns a SHA-256 checksum on success for integrity verification.

    Args:
        filename: The original filename including extension.
        content: The file content as bytes.
        content_type: The MIME type (e.g., "image/jpeg", "application/pdf").
        config: Validation configuration with allowed types, extensions, and size limits.

    Returns:
        Result containing:
            - Ok(str): SHA-256 checksum (64 hex characters) on successful validation
            - Err(UploadError): Specific error type on validation failure

    Raises:
        No exceptions raised - all errors returned as Result.Err

    Example:
        >>> config = FileValidationConfig(
        ...     max_size_bytes=10 * 1024 * 1024,
        ...     allowed_types=frozenset({"image/jpeg", "image/png"}),
        ...     allowed_extensions=frozenset({".jpg", ".jpeg", ".png"}),
        ... )
        >>> result = validate_file("photo.jpg", image_bytes, "image/jpeg", config)
        >>> if result.is_ok():
        ...     print(f"Checksum: {result.unwrap()}")
    """
    # Check file size
    if len(content) > config.max_size_bytes:
        return Err(UploadError.FILE_TOO_LARGE)

    # Check content type
    if content_type not in config.allowed_types:
        return Err(UploadError.INVALID_TYPE)

    # Check file extension
    ext = PurePath(filename.lower()).suffix
    if ext not in config.allowed_extensions:
        return Err(UploadError.INVALID_EXTENSION)

    # Validate magic bytes to prevent content-type spoofing
    if not validate_magic_bytes(content, content_type):
        return Err(UploadError.INVALID_TYPE)

    # Calculate checksum
    checksum = hashlib.sha256(content).hexdigest()

    return Ok(checksum)


def validate_file_stream(
    filename: str,
    stream: BinaryIO,
    content_type: str,
    config: FileValidationConfig,
) -> Result[tuple[bytes, str], UploadError]:
    """Validate a file from a stream (e.g., uploaded file).

    Similar to validate_file but reads from a stream. Validates content type
    and extension before reading to fail fast on invalid files.

    Args:
        filename: The original filename including extension.
        stream: File-like object supporting read() method.
        content_type: The MIME type from the upload request.
        config: Validation configuration with limits and allowed types.

    Returns:
        Result containing:
            - Ok(tuple[bytes, str]): (file_content, sha256_checksum) on success
            - Err(UploadError): Specific error type on validation failure

    Note:
        The stream is fully read into memory. For very large files,
        consider streaming validation with chunked reading.
    """
    # Check content type first
    if content_type not in config.allowed_types:
        return Err(UploadError.INVALID_TYPE)

    # Check file extension
    ext = PurePath(filename.lower()).suffix
    if ext not in config.allowed_extensions:
        return Err(UploadError.INVALID_EXTENSION)

    # Read and validate size
    content = stream.read()
    if len(content) > config.max_size_bytes:
        return Err(UploadError.FILE_TOO_LARGE)

    # Calculate checksum
    checksum = hashlib.sha256(content).hexdigest()

    return Ok((content, checksum))


def get_safe_filename(filename: str) -> str:
    """Sanitize a filename for safe storage.

    Removes or replaces dangerous characters that could be used for:
    - Path traversal attacks (../, ..\\)
    - Command injection (<, >, |, etc.)
    - Null byte injection (\\x00)
    - File system issues on various platforms

    Args:
        filename: The original filename, potentially containing malicious characters.

    Returns:
        Sanitized filename safe for storage. The name part is limited to 200
        characters while preserving the file extension.

    Security Notes:
        - Strips directory paths using os.path.basename()
        - Replaces: < > : " / \\ | ? * and null bytes with underscore
        - Truncates name part to 200 characters to prevent filesystem issues

    Example:
        >>> get_safe_filename("../../../etc/passwd")
        'passwd'
        >>> get_safe_filename("file<script>.txt")
        'file_script_.txt'
        >>> get_safe_filename("a" * 300 + ".pdf")
        'aaa...aaa.pdf'  # name truncated to 200 chars
    """
    # Remove path separators
    safe_name = PurePath(filename).name

    # Replace dangerous characters
    dangerous_chars = ["<", ">", ":", '"', "/", "\\", "|", "?", "*", "\x00"]
    for char in dangerous_chars:
        safe_name = safe_name.replace(char, "_")

    # Limit length
    path = PurePath(safe_name)
    name = path.stem
    ext = path.suffix
    if len(name) > 200:
        name = name[:200]

    return f"{name}{ext}"
