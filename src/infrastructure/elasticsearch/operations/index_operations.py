"""Elasticsearch index and document operations.

**Feature: observability-infrastructure**
**Requirement: R2.3 - Index & Document Management**
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)


class IndexOperations:
    """Handles Elasticsearch index management operations."""

    def __init__(self, client_getter: callable) -> None:
        """Initialize with client getter function.

        Args:
            client_getter: Async function that returns AsyncElasticsearch client
        """
        self._get_client = client_getter

    async def create_index(
        self,
        index: str,
        mappings: dict[str, Any] | None = None,
        settings: dict[str, Any] | None = None,
    ) -> bool:
        """Create an index.

        Args:
            index: Index name
            mappings: Index mappings
            settings: Index settings

        Returns:
            True if created successfully
        """
        client = await self._get_client()

        body: dict[str, Any] = {}
        if mappings:
            body["mappings"] = mappings
        if settings:
            body["settings"] = settings

        try:
            await client.indices.create(index=index, body=body if body else None)
            logger.info(f"Created index: {index}")
            return True
        except Exception as e:
            logger.error(f"Failed to create index {index}: {e}")
            raise

    async def delete_index(self, index: str) -> bool:
        """Delete an index.

        Args:
            index: Index name

        Returns:
            True if deleted successfully
        """
        client = await self._get_client()

        try:
            await client.indices.delete(index=index)
            logger.info(f"Deleted index: {index}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete index {index}: {e}")
            raise

    async def index_exists(self, index: str) -> bool:
        """Check if index exists.

        Args:
            index: Index name

        Returns:
            True if index exists
        """
        client = await self._get_client()
        return await client.indices.exists(index=index)

    async def refresh_index(self, index: str) -> None:
        """Refresh an index (make recent changes searchable).

        Args:
            index: Index name
        """
        client = await self._get_client()
        await client.indices.refresh(index=index)


class DocumentOperations:
    """Handles Elasticsearch document CRUD operations."""

    def __init__(self, client_getter: callable) -> None:
        """Initialize with client getter function.

        Args:
            client_getter: Async function that returns AsyncElasticsearch client
        """
        self._get_client = client_getter

    async def index_document(
        self,
        index: str,
        document: dict[str, Any],
        doc_id: str | None = None,
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Index a document.

        Args:
            index: Index name
            document: Document to index
            doc_id: Optional document ID
            refresh: Whether to refresh after indexing

        Returns:
            Index response with _id, _version, etc.
        """
        client = await self._get_client()

        result = await client.index(
            index=index,
            id=doc_id,
            document=document,
            refresh=refresh,
        )

        return dict(result)

    async def get_document(
        self,
        index: str,
        doc_id: str,
    ) -> dict[str, Any] | None:
        """Get a document by ID.

        Args:
            index: Index name
            doc_id: Document ID

        Returns:
            Document or None if not found
        """
        client = await self._get_client()

        try:
            result = await client.get(index=index, id=doc_id)
            return dict(result)
        except Exception:
            return None

    async def update_document(
        self,
        index: str,
        doc_id: str,
        document: dict[str, Any],
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Update a document.

        Args:
            index: Index name
            doc_id: Document ID
            document: Partial document with fields to update
            refresh: Whether to refresh after update

        Returns:
            Update response
        """
        client = await self._get_client()

        result = await client.update(
            index=index,
            id=doc_id,
            doc=document,
            refresh=refresh,
        )

        return dict(result)

    async def delete_document(
        self,
        index: str,
        doc_id: str,
        refresh: bool = False,
    ) -> bool:
        """Delete a document.

        Args:
            index: Index name
            doc_id: Document ID
            refresh: Whether to refresh after delete

        Returns:
            True if deleted
        """
        client = await self._get_client()

        try:
            await client.delete(index=index, id=doc_id, refresh=refresh)
            return True
        except Exception:
            return False

    async def bulk(
        self,
        operations: list[dict[str, Any]],
        refresh: bool = False,
    ) -> dict[str, Any]:
        """Execute bulk operations.

        Args:
            operations: List of bulk operations
            refresh: Whether to refresh after bulk

        Returns:
            Bulk response
        """
        client = await self._get_client()

        result = await client.bulk(operations=operations, refresh=refresh)
        return dict(result)
