"""Unit tests for batch configuration.

**Feature: test-coverage-90-percent**
**Validates: Requirements 1.2**
"""

import pytest

from application.common.batch.config.config import (
    BatchConfig,
    BatchErrorStrategy,
    BatchOperationStats,
    BatchOperationType,
    BatchProgress,
    BatchResult,
)


class TestBatchOperationType:
    """Tests for BatchOperationType enum."""

    def test_create_type(self) -> None:
        """CREATE should have correct value."""
        assert BatchOperationType.CREATE.value == "create"

    def test_update_type(self) -> None:
        """UPDATE should have correct value."""
        assert BatchOperationType.UPDATE.value == "update"

    def test_delete_type(self) -> None:
        """DELETE should have correct value."""
        assert BatchOperationType.DELETE.value == "delete"

    def test_upsert_type(self) -> None:
        """UPSERT should have correct value."""
        assert BatchOperationType.UPSERT.value == "upsert"


class TestBatchErrorStrategy:
    """Tests for BatchErrorStrategy enum."""

    def test_fail_fast_strategy(self) -> None:
        """FAIL_FAST should have correct value."""
        assert BatchErrorStrategy.FAIL_FAST.value == "fail_fast"

    def test_continue_strategy(self) -> None:
        """CONTINUE should have correct value."""
        assert BatchErrorStrategy.CONTINUE.value == "continue"

    def test_rollback_strategy(self) -> None:
        """ROLLBACK should have correct value."""
        assert BatchErrorStrategy.ROLLBACK.value == "rollback"


class TestBatchResult:
    """Tests for BatchResult dataclass."""

    def test_create_successful_result(self) -> None:
        """BatchResult should store successful items."""
        result = BatchResult(
            succeeded=["item1", "item2"],
            failed=[],
            total_processed=2,
            total_succeeded=2,
            total_failed=0
        )
        
        assert result.succeeded == ["item1", "item2"]
        assert result.total_succeeded == 2
        assert result.total_failed == 0

    def test_create_result_with_failures(self) -> None:
        """BatchResult should store failed items."""
        error = ValueError("test error")
        result = BatchResult(
            succeeded=["item1"],
            failed=[("item2", error)],
            total_processed=2,
            total_succeeded=1,
            total_failed=1
        )
        
        assert result.total_succeeded == 1
        assert result.total_failed == 1
        assert len(result.failed) == 1

    def test_success_rate_calculation(self) -> None:
        """BatchResult should calculate success rate correctly."""
        result = BatchResult(
            succeeded=["item1", "item2"],
            failed=[("item3", ValueError("error"))],
            total_processed=3,
            total_succeeded=2,
            total_failed=1
        )
        
        assert result.success_rate == pytest.approx(66.67, rel=0.01)

    def test_success_rate_zero_processed(self) -> None:
        """BatchResult should return 100% for zero processed."""
        result = BatchResult(
            succeeded=[],
            failed=[],
            total_processed=0,
            total_succeeded=0,
            total_failed=0
        )
        
        assert result.success_rate == 100.0

    def test_is_complete_success(self) -> None:
        """BatchResult should detect complete success."""
        result = BatchResult(
            succeeded=["item1"],
            failed=[],
            total_processed=1,
            total_succeeded=1,
            total_failed=0
        )
        
        assert result.is_complete_success is True

    def test_has_failures(self) -> None:
        """BatchResult should detect failures."""
        result = BatchResult(
            succeeded=[],
            failed=[("item1", ValueError("error"))],
            total_processed=1,
            total_succeeded=0,
            total_failed=1
        )
        
        assert result.has_failures is True

    def test_rolled_back_result(self) -> None:
        """BatchResult should track rollback status."""
        result = BatchResult(
            succeeded=[],
            failed=[],
            total_processed=1,
            total_succeeded=0,
            total_failed=1,
            rolled_back=True,
            rollback_error=None
        )
        
        assert result.rolled_back is True
        assert result.has_failures is True


class TestBatchConfig:
    """Tests for BatchConfig dataclass."""

    def test_default_config(self) -> None:
        """BatchConfig should have sensible defaults."""
        config = BatchConfig()
        
        assert config.chunk_size == 100
        assert config.max_concurrent == 5
        assert config.error_strategy == BatchErrorStrategy.CONTINUE
        assert config.max_retries == 3

    def test_custom_config(self) -> None:
        """BatchConfig should accept custom values."""
        config = BatchConfig(
            chunk_size=50,
            error_strategy=BatchErrorStrategy.FAIL_FAST,
            max_retries=5
        )
        
        assert config.chunk_size == 50
        assert config.error_strategy == BatchErrorStrategy.FAIL_FAST
        assert config.max_retries == 5

    def test_invalid_chunk_size(self) -> None:
        """BatchConfig should reject invalid chunk_size."""
        with pytest.raises(ValueError, match="chunk_size must be positive"):
            BatchConfig(chunk_size=0)

    def test_invalid_max_concurrent(self) -> None:
        """BatchConfig should reject invalid max_concurrent."""
        with pytest.raises(ValueError, match="max_concurrent must be positive"):
            BatchConfig(max_concurrent=0)

    def test_invalid_max_retries(self) -> None:
        """BatchConfig should reject negative max_retries."""
        with pytest.raises(ValueError, match="max_retries must be non-negative"):
            BatchConfig(max_retries=-1)

    def test_invalid_timeout(self) -> None:
        """BatchConfig should reject invalid timeout."""
        with pytest.raises(ValueError, match="timeout_per_chunk must be positive"):
            BatchConfig(timeout_per_chunk=0)


class TestBatchProgress:
    """Tests for BatchProgress dataclass."""

    def test_progress_calculation(self) -> None:
        """BatchProgress should calculate percentage correctly."""
        progress = BatchProgress(
            total_items=100,
            processed_items=50,
            succeeded_items=45,
            failed_items=5
        )
        
        assert progress.total_items == 100
        assert progress.processed_items == 50
        assert progress.progress_percentage == 50.0

    def test_progress_zero_total(self) -> None:
        """BatchProgress should handle zero total."""
        progress = BatchProgress(
            total_items=0,
            processed_items=0,
            succeeded_items=0,
            failed_items=0
        )
        
        assert progress.progress_percentage == 100.0

    def test_is_complete(self) -> None:
        """BatchProgress should detect completion."""
        progress = BatchProgress(
            total_items=10,
            processed_items=10,
            succeeded_items=10,
            failed_items=0
        )
        
        assert progress.is_complete is True

    def test_not_complete(self) -> None:
        """BatchProgress should detect incomplete state."""
        progress = BatchProgress(
            total_items=10,
            processed_items=5,
            succeeded_items=5,
            failed_items=0
        )
        
        assert progress.is_complete is False


class TestBatchOperationStats:
    """Tests for BatchOperationStats dataclass."""

    def test_stats_creation(self) -> None:
        """BatchOperationStats should store timing info."""
        stats = BatchOperationStats(
            operation_type=BatchOperationType.CREATE,
            total_items=100,
            succeeded=95,
            failed=5,
            duration_ms=10500.0,
            items_per_second=10.0
        )
        
        assert stats.operation_type == BatchOperationType.CREATE
        assert stats.total_items == 100
        assert stats.succeeded == 95
        assert stats.failed == 5
        assert stats.duration_ms == 10500.0

    def test_stats_success_rate(self) -> None:
        """BatchOperationStats should calculate success rate."""
        stats = BatchOperationStats(
            operation_type=BatchOperationType.UPDATE,
            total_items=100,
            succeeded=80,
            failed=20
        )
        
        assert stats.success_rate == 80.0

    def test_stats_success_rate_zero_items(self) -> None:
        """BatchOperationStats should handle zero items."""
        stats = BatchOperationStats(
            operation_type=BatchOperationType.DELETE,
            total_items=0,
            succeeded=0,
            failed=0
        )
        
        assert stats.success_rate == 100.0
