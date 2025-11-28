"""Test factories for generating test data."""

from tests.factories.generic_fixtures import (
    MapperTestCase,
    RepositoryTestCase,
    TestContext,
    UseCaseTestCase,
    create_in_memory_repository,
    create_test_context,
)
from tests.factories.hypothesis_strategies import (
    create_dto_strategy,
    create_model_strategy,
    datetime_strategy,
    email_strategy,
    entity_strategy,
    list_of,
    one_of_models,
    optional,
    page_number_strategy,
    page_size_strategy,
    pydantic_strategy,
    strategy_for_field,
    ulid_strategy,
    update_dto_strategy,
    uuid_strategy,
)
from tests.factories.mock_repository import (
    CallRecord,
    MethodCallTracker,
    MockRepository,
    MockRepositoryFactory,
    TypedMock,
    create_typed_mock,
)

__all__ = [
    # Generic Test Fixtures
    "MapperTestCase",
    "RepositoryTestCase",
    "TestContext",
    "UseCaseTestCase",
    "create_in_memory_repository",
    "create_test_context",
    # Mock Repository
    "MockRepository",
    "MockRepositoryFactory",
    # Type-safe Mocks
    "TypedMock",
    "create_typed_mock",
    "CallRecord",
    "MethodCallTracker",
    # Hypothesis Strategies
    "pydantic_strategy",
    "entity_strategy",
    "create_dto_strategy",
    "update_dto_strategy",
    "ulid_strategy",
    "uuid_strategy",
    "email_strategy",
    "datetime_strategy",
    "page_number_strategy",
    "page_size_strategy",
    "list_of",
    "optional",
    "one_of_models",
    "strategy_for_field",
    "create_model_strategy",
]
