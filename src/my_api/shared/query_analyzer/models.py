"""query_analyzer models.

**Feature: shared-modules-phase3-fixes, Task 5.3**
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC
from typing import Any

from .enums import QueryType


@dataclass
class QueryMetrics:
    """Query execution metrics.

    Attributes:
        query: The SQL query.
        query_type: Type of query.
        execution_time_ms: Execution time in milliseconds.
        rows_examined: Number of rows examined.
        rows_returned: Number of rows returned.
        timestamp: When query was executed.
        explain_plan: Query explain plan if available.
    """

    query: str
    query_type: QueryType
    execution_time_ms: float
    rows_examined: int = 0
    rows_returned: int = 0
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    explain_plan: dict[str, Any] | None = None


@dataclass
class IndexSuggestion:
    """Index suggestion for query optimization.

    Attributes:
        table: Table name.
        columns: Columns to index.
        index_type: Type of index (btree, hash, etc.).
        reason: Reason for suggestion.
        estimated_improvement: Estimated improvement percentage.
    """

    table: str
    columns: list[str]
    index_type: str = "btree"
    reason: str = ""
    estimated_improvement: float = 0.0
