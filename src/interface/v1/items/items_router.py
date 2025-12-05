"""Item API routes."""

from application.mappers.item_mapper import ItemMapper
from application.use_cases.item_use_case import ItemUseCase
from core.base.repository import InMemoryRepository
from domain.entities.item import Item, ItemCreate, ItemResponse, ItemUpdate
from interface.router import GenericCRUDRouter

# Singleton mapper instance
_item_mapper = ItemMapper()

# Singleton in-memory repository for demo purposes
# In production, this would be replaced with SQLModelRepository via DI
_item_repository: InMemoryRepository[Item, ItemCreate, ItemUpdate] = InMemoryRepository(
    Item
)


def get_item_use_case() -> ItemUseCase:
    """Dependency to get ItemUseCase.

    Uses in-memory repository for demo purposes.
    In production, configure via DI container with SQLModelRepository.

    Returns:
        ItemUseCase instance.
    """
    return ItemUseCase(_item_repository, _item_mapper)


# Create the generic CRUD router for items
item_router = GenericCRUDRouter(
    prefix="/items",
    tags=["Items"],
    response_model=ItemResponse,
    create_model=ItemCreate,
    update_model=ItemUpdate,
    use_case_dependency=get_item_use_case,
)

router = item_router.router
