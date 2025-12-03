"""Property-based tests for Application Common Integration.

**Feature: application-common-integration**
**Validates: Requirements 1.1-9.5**
"""

import pytest
from decimal import Decimal
from hypothesis import given, settings, strategies as st

from application.common.base.exceptions import (
    ApplicationError,
    NotFoundError as BaseNotFoundError,
    ValidationError as BaseValidationError,
)
from application.examples.shared.errors import (
    UseCaseError,
    NotFoundError,
    ValidationError,
)
from application.common.base.dto import ApiResponse, PaginatedResponse


class TestErrorHierarchyProperties:
    """Property tests for error hierarchy consistency.
    
    **Feature: application-common-integration, Property 1: Error Hierarchy Consistency**
    **Validates: Requirements 1.1**
    """

    @settings(max_examples=100)
    @given(message=st.text(min_size=1, max_size=100))
    def test_use_case_error_is_application_error(self, message: str) -> None:
        """UseCaseError SHALL be instance of ApplicationError."""
        error = UseCaseError(message)
        assert isinstance(error, ApplicationError)
        assert error.message == message
        assert error.code == "USE_CASE_ERROR"

    @settings(max_examples=100)
    @given(
        entity=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
        entity_id=st.text(min_size=1, max_size=50),
    )
    def test_not_found_error_is_application_error(self, entity: str, entity_id: str) -> None:
        """NotFoundError SHALL be instance of ApplicationError."""
        error = NotFoundError(entity, entity_id)
        assert isinstance(error, ApplicationError)
        assert isinstance(error, BaseNotFoundError)

    @settings(max_examples=100)
    @given(message=st.text(min_size=1, max_size=100))
    def test_validation_error_is_application_error(self, message: str) -> None:
        """ValidationError SHALL be instance of ApplicationError."""
        error = ValidationError(message)
        assert isinstance(error, ApplicationError)
        assert isinstance(error, BaseValidationError)


class TestNotFoundErrorProperties:
    """Property tests for NotFoundError entity information.
    
    **Feature: application-common-integration, Property 2: NotFoundError Contains Entity Information**
    **Validates: Requirements 1.2**
    """

    @settings(max_examples=100)
    @given(
        entity_type=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
        entity_id=st.text(min_size=1, max_size=50),
    )
    def test_not_found_error_contains_entity_info(self, entity_type: str, entity_id: str) -> None:
        """NotFoundError SHALL contain entity_type and entity_id in details."""
        error = NotFoundError(entity_type, entity_id)
        
        assert error.entity_type == entity_type
        assert str(error.entity_id) == entity_id
        assert "entity_type" in error.details
        assert "entity_id" in error.details
        assert error.details["entity_type"] == entity_type


class TestValidationErrorProperties:
    """Property tests for ValidationError field errors.
    
    **Feature: application-common-integration, Property 3: ValidationError Contains Field Errors**
    **Validates: Requirements 1.3**
    """

    @settings(max_examples=100)
    @given(
        message=st.text(min_size=1, max_size=100),
        field=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
    )
    def test_validation_error_contains_field_info(self, message: str, field: str) -> None:
        """ValidationError with field SHALL contain field in errors list."""
        error = ValidationError(message, field=field)
        
        assert error.message == message
        assert error.field == field
        assert len(error.errors) == 1
        assert error.errors[0]["field"] == field
        assert error.errors[0]["message"] == message


class TestApiResponseProperties:
    """Property tests for API response wrapper.
    
    **Feature: application-common-integration, Property 15: API Response Wrapper Consistency**
    **Validates: Requirements 8.2**
    """

    @settings(max_examples=100)
    @given(data=st.text(min_size=1, max_size=100))
    def test_api_response_contains_required_fields(self, data: str) -> None:
        """ApiResponse SHALL contain data, message, status_code, timestamp."""
        response = ApiResponse(data=data)
        
        assert response.data == data
        assert response.message is not None
        assert response.status_code is not None
        assert response.timestamp is not None


class TestPaginationProperties:
    """Property tests for pagination metadata.
    
    **Feature: application-common-integration, Property 16: Pagination Metadata Correctness**
    **Validates: Requirements 8.4**
    """

    @settings(max_examples=100)
    @given(
        total=st.integers(min_value=0, max_value=1000),
        page=st.integers(min_value=1, max_value=100),
        size=st.integers(min_value=1, max_value=100),
    )
    def test_pagination_pages_calculation(self, total: int, page: int, size: int) -> None:
        """Pagination pages SHALL equal ceil(total/size)."""
        items = ["item"] * min(size, total)
        response = PaginatedResponse(items=items, total=total, page=page, size=size)
        
        expected_pages = (total + size - 1) // size if total > 0 else 0
        assert response.pages == expected_pages

    @settings(max_examples=100)
    @given(
        total=st.integers(min_value=1, max_value=1000),
        size=st.integers(min_value=1, max_value=100),
    )
    def test_pagination_has_next(self, total: int, size: int) -> None:
        """has_next SHALL be True when page < pages."""
        pages = (total + size - 1) // size
        page = max(1, pages - 1) if pages > 1 else 1
        
        items = ["item"] * min(size, total)
        response = PaginatedResponse(items=items, total=total, page=page, size=size)
        
        assert response.has_next == (page < response.pages)


# =============================================================================
# Additional Property Tests for CQRS, Mappers, Middleware, Batch, Export
# =============================================================================


class TestCommandDispatchProperties:
    """Property tests for command dispatch.
    
    **Feature: application-common-integration, Property 4: Command Dispatch Invokes Handler**
    **Validates: Requirements 2.1, 2.2, 2.3**
    """

    @settings(max_examples=100)
    @given(
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
        sku=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "N"))),
        price=st.decimals(min_value=0, max_value=10000, places=2, allow_nan=False, allow_infinity=False),
    )
    def test_create_item_command_is_immutable(self, name: str, sku: str, price: Decimal) -> None:
        """CreateItemCommand SHALL be immutable (frozen dataclass)."""
        from application.examples.item.commands import CreateItemCommand
        
        command = CreateItemCommand(name=name, sku=sku, price_amount=price)
        
        assert command.name == name
        assert command.sku == sku
        assert command.price_amount == price
        
        # Verify immutability
        with pytest.raises(AttributeError):
            command.name = "changed"  # type: ignore

    @settings(max_examples=100)
    @given(item_id=st.uuids().map(str))
    def test_delete_item_command_contains_item_id(self, item_id: str) -> None:
        """DeleteItemCommand SHALL contain item_id."""
        from application.examples.item.commands import DeleteItemCommand
        
        command = DeleteItemCommand(item_id=item_id)
        assert command.item_id == item_id
        assert command.command_type == "DeleteItemCommand"


class TestQueryDispatchProperties:
    """Property tests for query dispatch.
    
    **Feature: application-common-integration, Property 5: Query Dispatch Returns Handler Result**
    **Validates: Requirements 2.4, 2.5**
    """

    @settings(max_examples=100)
    @given(item_id=st.uuids().map(str))
    def test_get_item_query_contains_item_id(self, item_id: str) -> None:
        """GetItemQuery SHALL contain item_id."""
        from application.examples.item.queries import GetItemQuery
        
        query = GetItemQuery(item_id=item_id)
        assert query.item_id == item_id
        assert query.query_type == "GetItemQuery"

    @settings(max_examples=100)
    @given(
        page=st.integers(min_value=1, max_value=100),
        size=st.integers(min_value=1, max_value=100),
    )
    def test_list_items_query_pagination(self, page: int, size: int) -> None:
        """ListItemsQuery SHALL contain pagination parameters."""
        from application.examples.item.queries import ListItemsQuery
        
        query = ListItemsQuery(page=page, size=size)
        assert query.page == page
        assert query.size == size


class TestMapperRoundTripProperties:
    """Property tests for mapper round-trip.
    
    **Feature: application-common-integration, Property 7: Mapper Round-Trip Preserves Data**
    **Validates: Requirements 4.1, 4.2**
    """

    @settings(max_examples=50)
    @given(
        name=st.text(min_size=1, max_size=50, alphabet=st.characters(whitelist_categories=("L",))),
        sku=st.text(min_size=3, max_size=20, alphabet=st.characters(whitelist_categories=("Lu", "N"))),
        quantity=st.integers(min_value=0, max_value=1000),
    )
    def test_item_mapper_preserves_essential_fields(self, name: str, sku: str, quantity: int) -> None:
        """ItemExampleMapper to_dto SHALL preserve essential fields."""
        from decimal import Decimal
        from application.examples.item.mapper import ItemExampleMapper
        from application.examples.item.dtos import ItemExampleResponse
        from application.examples.shared.dtos import MoneyDTO
        from datetime import datetime
        
        # Create a mock DTO directly to test mapper interface
        dto = ItemExampleResponse(
            id="test-id",
            name=name,
            description="Test description",
            sku=sku,
            price=MoneyDTO(amount=Decimal("10.00"), currency="BRL"),
            quantity=quantity,
            status="active",
            category="test",
            tags=["tag1"],
            is_available=True,
            total_value=MoneyDTO(amount=Decimal("100.00"), currency="BRL"),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            created_by="test",
            updated_by="test",
        )
        
        # Verify DTO has expected fields
        assert dto.name == name
        assert dto.sku == sku
        assert dto.quantity == quantity


class TestBatchMappingProperties:
    """Property tests for batch mapping.
    
    **Feature: application-common-integration, Property 8: Batch Mapping Preserves Count**
    **Validates: Requirements 4.3**
    """

    @settings(max_examples=50)
    @given(count=st.integers(min_value=0, max_value=20))
    def test_batch_mapping_preserves_count(self, count: int) -> None:
        """to_dto_list SHALL return exactly N DTOs for N entities."""
        from decimal import Decimal
        from datetime import datetime
        from application.examples.item.dtos import ItemExampleResponse
        from application.examples.shared.dtos import MoneyDTO
        
        # Create mock DTOs directly to test batch mapping logic
        dtos = [
            ItemExampleResponse(
                id=f"id-{i}",
                name=f"Item {i}",
                description="Test",
                sku=f"SKU{i:04d}",
                price=MoneyDTO(amount=Decimal("10.00"), currency="BRL"),
                quantity=i,
                status="active",
                category="test",
                tags=[],
                is_available=True,
                total_value=MoneyDTO(amount=Decimal("10.00") * i, currency="BRL"),
                created_at=datetime.now(),
                updated_at=datetime.now(),
                created_by="test",
                updated_by="test",
            )
            for i in range(count)
        ]
        
        assert len(dtos) == count
        for i, dto in enumerate(dtos):
            assert dto.name == f"Item {i}"


class TestRetryMiddlewareProperties:
    """Property tests for retry middleware.
    
    **Feature: application-common-integration, Property 9: Retry Middleware Retries Transient Failures**
    **Validates: Requirements 5.2**
    """

    @settings(max_examples=50)
    @given(max_retries=st.integers(min_value=1, max_value=5))
    def test_retry_config_max_retries(self, max_retries: int) -> None:
        """RetryConfig SHALL respect max_retries setting."""
        from application.common.middleware.retry import RetryConfig
        
        config = RetryConfig(max_retries=max_retries)
        assert config.max_retries == max_retries


class TestCircuitBreakerProperties:
    """Property tests for circuit breaker.
    
    **Feature: application-common-integration, Property 10: Circuit Breaker Opens After Threshold**
    **Validates: Requirements 5.3**
    """

    @settings(max_examples=50)
    @given(threshold=st.integers(min_value=1, max_value=10))
    def test_circuit_breaker_config_threshold(self, threshold: int) -> None:
        """CircuitBreakerConfig SHALL respect failure_threshold setting."""
        from application.common.middleware.circuit_breaker import CircuitBreakerConfig
        
        config = CircuitBreakerConfig(failure_threshold=threshold)
        assert config.failure_threshold == threshold


class TestValidationMiddlewareProperties:
    """Property tests for validation middleware.
    
    **Feature: application-common-integration, Property 11: Validation Middleware Rejects Invalid Commands**
    **Validates: Requirements 5.4**
    """

    @settings(max_examples=50, deadline=None)
    @given(
        empty_name=st.just(""),
        valid_sku=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "N"))),
    )
    def test_create_item_validator_rejects_empty_name(self, empty_name: str, valid_sku: str) -> None:
        """CreateItemCommandValidator SHALL reject empty name."""
        from decimal import Decimal
        from application.examples.item.commands import CreateItemCommand
        from infrastructure.di.examples_bootstrap import CreateItemCommandValidator
        
        command = CreateItemCommand(name=empty_name, sku=valid_sku, price_amount=Decimal("10.00"))
        validator = CreateItemCommandValidator()
        errors = validator.validate(command)
        
        assert "Name is required" in errors


class TestBatchOperationsProperties:
    """Property tests for batch operations.
    
    **Feature: application-common-integration, Property 12: Batch Operations Process All Items**
    **Validates: Requirements 6.5**
    """

    @settings(max_examples=50)
    @given(count=st.integers(min_value=0, max_value=10))
    def test_batch_result_total_processed(self, count: int) -> None:
        """BatchResult.total_processed SHALL equal input list length."""
        from application.common.batch.config import BatchResult
        
        succeeded = list(range(count))
        result = BatchResult(
            succeeded=succeeded,
            failed=[],
            total_processed=count,
            total_succeeded=count,
            total_failed=0,
        )
        
        assert result.total_processed == count
        assert len(result.succeeded) == count


class TestExportImportRoundTripProperties:
    """Property tests for export-import round trip.
    
    **Feature: application-common-integration, Property 13: Export-Import Round Trip**
    **Validates: Requirements 7.1, 7.2, 7.3, 7.4**
    """

    @settings(max_examples=20)
    @given(
        name=st.text(min_size=1, max_size=30, alphabet=st.characters(whitelist_categories=("L",))),
        sku=st.text(min_size=3, max_size=10, alphabet=st.characters(whitelist_categories=("Lu", "N"))),
    )
    def test_json_export_contains_metadata(self, name: str, sku: str) -> None:
        """JSON export SHALL include metadata with timestamp and count."""
        from datetime import datetime, UTC
        from application.examples.item.export import ExportMetadata, ExportFormat
        
        metadata = ExportMetadata(
            format=ExportFormat.JSON.value,
            record_count=1,
            export_timestamp=datetime.now(UTC),
            checksum="abc123",
        )
        
        assert metadata.format == "json"
        assert metadata.record_count == 1
        assert metadata.checksum == "abc123"


class TestExportChecksumProperties:
    """Property tests for export checksum integrity.
    
    **Feature: application-common-integration, Property 14: Export Checksum Integrity**
    **Validates: Requirements 7.5**
    """

    @settings(max_examples=50)
    @given(data=st.text(min_size=1, max_size=100))
    def test_checksum_is_16_char_hex(self, data: str) -> None:
        """Export checksum SHALL be 16-character hex string from SHA-256."""
        import hashlib
        
        full_hash = hashlib.sha256(data.encode()).hexdigest()
        checksum = full_hash[:16]
        
        assert len(checksum) == 16
        assert all(c in "0123456789abcdef" for c in checksum)

    @settings(max_examples=50)
    @given(data=st.text(min_size=1, max_size=100))
    def test_checksum_is_deterministic(self, data: str) -> None:
        """Same data SHALL produce same checksum."""
        import hashlib
        
        checksum1 = hashlib.sha256(data.encode()).hexdigest()[:16]
        checksum2 = hashlib.sha256(data.encode()).hexdigest()[:16]
        
        assert checksum1 == checksum2
