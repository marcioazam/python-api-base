"""query_analyzer enums.

**Feature: shared-modules-phase3-fixes, Task 5.3**
"""

from enum import Enum


class QueryType(str, Enum):
    """SQL query types."""

    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    OTHER = "OTHER"


class OptimizationSuggestion(str, Enum):
    """Query optimization suggestions."""

    ADD_INDEX = "add_index"
    USE_COVERING_INDEX = "use_covering_index"
    AVOID_SELECT_STAR = "avoid_select_star"
    ADD_LIMIT = "add_limit"
    USE_EXISTS = "use_exists"
    AVOID_OR = "avoid_or"
    USE_UNION = "use_union"
    AVOID_FUNCTION_ON_COLUMN = "avoid_function_on_column"
    USE_PREPARED_STATEMENT = "use_prepared_statement"
    PARTITION_TABLE = "partition_table"
