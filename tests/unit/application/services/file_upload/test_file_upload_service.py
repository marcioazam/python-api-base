"""Unit tests for FileUploadService.

**Feature: test-coverage-90-percent**
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from application.services.file_upload.service.service import (
    FileUploadService,
    InMemoryStorageProvider,
)
from application.services.file_upload.models import (
    FileValidationConfig,
    UploadError,
)


class TestInMemoryStorageProvider:
    """Tests for InMemoryStorageProvider."""

    @pytest.fixture
    def provider(self) -> InMemoryStorageProvider:
        """Create provider instance."""
        return InMemoryStorageProvider()

    @pytest.mark.asyncio
    async def test_upload_stores_content(
        self, provider: InMemoryStorageProvider
    ) -> None:
        """Should store content in memory."""
        url = await provider.upload(
            "test-key",
            b"test content",
            "text/plain",
            {"custom": "metadata"},
        )

        assert url == "memory://test-key"
        assert await provider.exists("test-key")

    @pytest.mark.asyncio
    async def test_download_returns_content(
        self, provider: InMemoryStorageProvider
    ) -> None:
        """Should return stored content."""
        await provider.upload("test-key", b"test content", "text/plain", {})

        chunks = []
        async for chunk in provider.download("test-key"):
            chunks.append(chunk)

        assert b"".join(chunks) == b"test content"

    @pytest.mark.asyncio
    async def test_delete_removes_content(
        self, provider: InMemoryStorageProvider
    ) -> None:
        """Should remove content from storage."""
        await provider.upload("test-key", b"test content", "text/plain", {})

        result = await provider.delete("test-key")

        assert result is True
        assert await provider.exists("test-key") is False

    @pytest.mark.asyncio
    async def test_delete_nonexistent_returns_false(
        self, provider: InMemoryStorageProvider
    ) -> None:
        """Should return False for nonexistent key."""
        result = await provider.delete("nonexistent")
        assert result is False

    @pytest.mark.asyncio
    async def test_get_presigned_url(
        self, provider: InMemoryStorageProvider
    ) -> None:
        """Should generate mock presigned URL."""
        url = await provider.get_presigned_url("test-key", 7200, "PUT")

        assert "test-key" in url
        assert "expires=7200" in url
        assert "method=PUT" in url

    @pytest.mark.asyncio
    async def test_exists_returns_false_for_missing(
        self, provider: InMemoryStorageProvider
    ) -> None:
        """Should return False for missing key."""
        assert await provider.exists("missing") is False


class TestFileUploadService:
    """Tests for FileUploadService."""

    @pytest.fixture
    def mock_storage(self) -> AsyncMock:
        """Create mock storage provider."""
        storage = AsyncMock()
        storage.upload.return_value = "https://storage.example.com/file"
        storage.exists.return_value = True
        storage.delete.return_value = True
        storage.get_presigned_url.return_value = "https://presigned.url"
        return storage

    @pytest.fixture
    def config(self) -> FileValidationConfig:
        """Create validation config."""
        return FileValidationConfig(
            max_size_bytes=10 * 1024 * 1024,  # 10MB
            allowed_extensions=frozenset({".txt", ".pdf", ".jpg"}),
            allowed_types=frozenset({"text/plain", "application/pdf", "image/jpeg"}),
        )

    @pytest.fixture
    def service(
        self, mock_storage: AsyncMock, config: FileValidationConfig
    ) -> FileUploadService:
        """Create service instance."""
        return FileUploadService(mock_storage, config)

    @pytest.mark.asyncio
    async def test_upload_success(
        self, service: FileUploadService, mock_storage: AsyncMock
    ) -> None:
        """Should upload file successfully."""
        result = await service.upload(
            filename="test.txt",
            content=b"Hello, World!",
            content_type="text/plain",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        assert result.is_ok()
        upload_result = result.unwrap()
        assert upload_result.file_id is not None
        assert upload_result.metadata.filename == "test.txt"
        mock_storage.upload.assert_called_once()

    @pytest.mark.asyncio
    async def test_upload_invalid_extension(
        self, service: FileUploadService
    ) -> None:
        """Should reject invalid file extension."""
        result = await service.upload(
            filename="test.exe",
            content=b"malicious content",
            content_type="application/octet-stream",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        assert result.is_err()
        # Validation checks content type first, then extension
        assert result.error in (UploadError.INVALID_TYPE, UploadError.INVALID_EXTENSION)

    @pytest.mark.asyncio
    async def test_upload_exceeds_quota(
        self, service: FileUploadService
    ) -> None:
        """Should reject upload when quota exceeded."""
        service.set_quota("tenant-456", 100)  # 100 bytes limit

        result = await service.upload(
            filename="test.txt",
            content=b"x" * 200,  # 200 bytes
            content_type="text/plain",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        assert result.is_err()
        assert result.error == UploadError.QUOTA_EXCEEDED

    @pytest.mark.asyncio
    async def test_quota_management(self, service: FileUploadService) -> None:
        """Should track quota usage."""
        service.set_quota("tenant-123", 1000)

        used, limit = service.get_quota_usage("tenant-123")
        assert used == 0
        assert limit == 1000

    @pytest.mark.asyncio
    async def test_upload_updates_quota(
        self, service: FileUploadService, mock_storage: AsyncMock
    ) -> None:
        """Should update quota after successful upload."""
        service.set_quota("tenant-456", 10000)

        await service.upload(
            filename="test.txt",
            content=b"Hello!",
            content_type="text/plain",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        used, _ = service.get_quota_usage("tenant-456")
        assert used == 6  # len(b"Hello!")

    @pytest.mark.asyncio
    async def test_delete_updates_quota(
        self, service: FileUploadService, mock_storage: AsyncMock
    ) -> None:
        """Should update quota after delete."""
        service.set_quota("tenant-456", 10000)
        service._quotas["tenant-456"] = 100

        await service.delete("storage-key", "tenant-456", 50)

        used, _ = service.get_quota_usage("tenant-456")
        assert used == 50

    @pytest.mark.asyncio
    async def test_get_presigned_url(
        self, service: FileUploadService, mock_storage: AsyncMock
    ) -> None:
        """Should delegate to storage provider."""
        url = await service.get_presigned_url("key", 3600, "GET")

        assert url == "https://presigned.url"
        mock_storage.get_presigned_url.assert_called_once_with("key", 3600, "GET")

    @pytest.mark.asyncio
    async def test_exists(
        self, service: FileUploadService, mock_storage: AsyncMock
    ) -> None:
        """Should delegate to storage provider."""
        result = await service.exists("key")

        assert result is True
        mock_storage.exists.assert_called_once_with("key")

    @pytest.mark.asyncio
    async def test_upload_storage_error(
        self, service: FileUploadService, mock_storage: AsyncMock
    ) -> None:
        """Should handle storage errors."""
        mock_storage.upload.side_effect = Exception("Storage failed")

        result = await service.upload(
            filename="test.txt",
            content=b"content",
            content_type="text/plain",
            user_id="user-123",
            tenant_id="tenant-456",
        )

        assert result.is_err()
        assert result.error == UploadError.STORAGE_ERROR
