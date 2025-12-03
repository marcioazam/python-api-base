"""Batch operations for ItemExample.

**Feature: application-common-integration**
**Validates: Requirements 6.1, 6.2, 6.3, 6.4**
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

from application.common.batch.config import BatchConfig, BatchErrorStrategy as ErrorStrategy
from application.common.batch.config import BatchResult
from application.examples.item.dtos import ItemExampleResponse
from application.examples.item.mapper import ItemExampleMapper
from domain.examples.item.entity import ItemExample, Money


@dataclass
class BatchCreateRequest:
    """Request for batch item creation."""
    
    name: str
    sku: str
    price_amount: float
    price_currency: str = "BRL"
    description: str = ""
    quantity: int = 0
    category: str = ""
    tags: list[str] = field(default_factory=list)


@dataclass
class BatchUpdateRequest:
    """Request for batch item update."""
    
    item_id: str
    name: str | None = None
    description: str | None = None
    price_amount: float | None = None
    quantity: int | None = None
    category: str | None = None


class ItemExampleBatchService:
    """Service for batch operations on ItemExample entities.
    
    Supports bulk create, update, and delete with progress tracking.
    """
    
    def __init__(
        self,
        repository: Any,
        config: BatchConfig | None = None,
    ) -> None:
        """Initialize batch service.
        
        Args:
            repository: ItemExample repository.
            config: Batch configuration (optional).
        """
        self._repo = repository
        self._config = config or BatchConfig(
            chunk_size=100,
            error_strategy=ErrorStrategy.CONTINUE,
        )
        self._mapper = ItemExampleMapper()
    
    async def batch_create(
        self,
        items: list[BatchCreateRequest],
        created_by: str = "system",
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> BatchResult[ItemExampleResponse]:
        """Create multiple items in batches.
        
        Args:
            items: List of items to create.
            created_by: User creating the items.
            progress_callback: Optional callback for progress updates.
        
        Returns:
            BatchResult with succeeded and failed items.
        """
        succeeded: list[ItemExampleResponse] = []
        failed: list[tuple[int, str]] = []
        total = len(items)
        
        for i, item_data in enumerate(items):
            try:
                entity = ItemExample.create(
                    name=item_data.name,
                    description=item_data.description,
                    sku=item_data.sku,
                    price=Money(item_data.price_amount, item_data.price_currency),
                    quantity=item_data.quantity,
                    category=item_data.category,
                    tags=list(item_data.tags),
                    created_by=created_by,
                )
                saved = await self._repo.create(entity)
                succeeded.append(self._mapper.to_dto(saved))
            except Exception as e:
                if self._config.error_strategy == ErrorStrategy.FAIL_FAST:
                    raise
                failed.append((i, str(e)))
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return BatchResult(
            succeeded=succeeded,
            failed=failed,
            total_processed=total,
        )
    
    async def batch_update(
        self,
        updates: list[BatchUpdateRequest],
        updated_by: str = "system",
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> BatchResult[ItemExampleResponse]:
        """Update multiple items in batches.
        
        Args:
            updates: List of update requests.
            updated_by: User updating the items.
            progress_callback: Optional callback for progress updates.
        
        Returns:
            BatchResult with succeeded and failed items.
        """
        succeeded: list[ItemExampleResponse] = []
        failed: list[tuple[int, str]] = []
        total = len(updates)
        
        for i, update_data in enumerate(updates):
            try:
                entity = await self._repo.get(update_data.item_id)
                if not entity:
                    failed.append((i, f"Item {update_data.item_id} not found"))
                    continue
                
                if update_data.name is not None:
                    entity.name = update_data.name
                if update_data.description is not None:
                    entity.description = update_data.description
                if update_data.price_amount is not None:
                    entity.price = Money(update_data.price_amount, entity.price.currency)
                if update_data.quantity is not None:
                    entity.quantity = update_data.quantity
                if update_data.category is not None:
                    entity.category = update_data.category
                
                entity.mark_updated_by(updated_by)
                saved = await self._repo.update(entity)
                succeeded.append(self._mapper.to_dto(saved))
            except Exception as e:
                if self._config.error_strategy == ErrorStrategy.FAIL_FAST:
                    raise
                failed.append((i, str(e)))
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return BatchResult(
            succeeded=succeeded,
            failed=failed,
            total_processed=total,
        )
    
    async def batch_delete(
        self,
        item_ids: list[str],
        deleted_by: str = "system",
        hard_delete: bool = False,
        progress_callback: Callable[[int, int], None] | None = None,
    ) -> BatchResult[str]:
        """Delete multiple items in batches.
        
        Args:
            item_ids: List of item IDs to delete.
            deleted_by: User deleting the items.
            hard_delete: If True, permanently delete; otherwise soft delete.
            progress_callback: Optional callback for progress updates.
        
        Returns:
            BatchResult with succeeded and failed item IDs.
        """
        succeeded: list[str] = []
        failed: list[tuple[int, str]] = []
        total = len(item_ids)
        
        for i, item_id in enumerate(item_ids):
            try:
                entity = await self._repo.get(item_id)
                if not entity:
                    failed.append((i, f"Item {item_id} not found"))
                    continue
                
                if hard_delete:
                    await self._repo.delete(item_id)
                else:
                    entity.soft_delete(deleted_by)
                    await self._repo.update(entity)
                
                succeeded.append(item_id)
            except Exception as e:
                if self._config.error_strategy == ErrorStrategy.FAIL_FAST:
                    raise
                failed.append((i, str(e)))
            
            if progress_callback:
                progress_callback(i + 1, total)
        
        return BatchResult(
            succeeded=succeeded,
            failed=failed,
            total_processed=total,
        )
