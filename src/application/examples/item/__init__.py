"""Application layer for ItemExample.

Organized into subpackages by responsibility:
- commands/: Item commands
- queries/: Item queries
- handlers/: Command/Query handlers
- use_cases/: Business logic
- dtos/: Data transfer objects
- mappers/: Entity ↔ DTO mapping
- batch/: Batch operations
- export/: Export functionality

**Feature: application-common-integration**
"""

from application.examples.item.batch import (
    BatchCreateRequest,
    BatchUpdateRequest,
    ItemExampleBatchService,
)
from application.examples.item.commands import (
    CreateItemCommand,
    DeleteItemCommand,
    UpdateItemCommand,
)
from application.examples.item.dtos import (
    ItemExampleCreate,
    ItemExampleResponse,
    ItemExampleUpdate,
)
from application.examples.item.export import (
    ExportFormat,
    ExportMetadata,
    ExportResult,
    ImportResult,
    ItemExampleExportService,
    ItemExampleImportService,
)
from application.examples.item.handlers import (
    CreateItemHandler,
    DeleteItemHandler,
    GetItemByIdHandler,
    ListItemsHandler,
    UpdateItemHandler,
)
from application.examples.item.mappers import ItemExampleMapper
from application.examples.item.queries import (
    GetItemByIdQuery,
    ListItemsQuery,
)
from application.examples.item.use_cases import ItemExampleUseCase

__all__ = [
    # Commands
    "CreateItemCommand",
    "UpdateItemCommand",
    "DeleteItemCommand",
    # Queries
    "GetItemByIdQuery",
    "ListItemsQuery",
    # Handlers
    "CreateItemHandler",
    "UpdateItemHandler",
    "DeleteItemHandler",
    "GetItemByIdHandler",
    "ListItemsHandler",
    # DTOs
    "ItemExampleCreate",
    "ItemExampleUpdate",
    "ItemExampleResponse",
    # Mapper
    "ItemExampleMapper",
    # Batch
    "BatchCreateRequest",
    "BatchUpdateRequest",
    "ItemExampleBatchService",
    # Export
    "ExportFormat",
    "ExportMetadata",
    "ExportResult",
    "ImportResult",
    "ItemExampleExportService",
    "ItemExampleImportService",
    # Use Case
    "ItemExampleUseCase",
]
