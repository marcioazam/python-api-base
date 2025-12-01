"""query_analyzer service."""

import re
from typing import Any

from pydantic import BaseModel

from .config import AnalyzerConfig
from .constants import ALLOWED_IDENTIFIER_PATTERN, MAX_QUERY_LENGTH
from .enums import OptimizationSuggestion, QueryType
from .models import IndexSuggestion, QueryMetrics


class QueryAnalysis(BaseModel):
    """Query analysis result.

    Attributes:
        query: Original query.
        query_type: Type of query.
        tables: Tables involved.
        columns: Columns referenced.
        has_where: Whether query has WHERE clause.
        has_join: Whether query has JOIN.
        has_subquery: Whether query has subquery.
        has_order_by: Whether query has ORDER BY.
        has_limit: Whether query has LIMIT.
        suggestions: Optimization suggestions.
        index_suggestions: Index suggestions.
        estimated_cost: Estimated query cost.
    """

    query: str
    query_type: QueryType
    tables: list[str] = []
    columns: list[str] = []
    has_where: bool = False
    has_join: bool = False
    has_subquery: bool = False
    has_order_by: bool = False
    has_limit: bool = False
    suggestions: list[OptimizationSuggestion] = []
    index_suggestions: list[IndexSuggestion] = []
    estimated_cost: float = 0.0

    model_config = {"arbitrary_types_allowed": True}

class QueryAnalyzer:
    """SQL query analyzer.

    Analyzes queries for performance issues and suggests optimizations.
    """

    def __init__(self, config: AnalyzerConfig | None = None) -> None:
        """Initialize query analyzer.

        Args:
            config: Analyzer configuration.
        """
        self._config = config or AnalyzerConfig()
        self._queries: list[QueryMetrics] = []
        self._slow_queries: list[QueryMetrics] = []

    def _validate_query(self, query: str) -> None:
        """Validate query input for security.

        Args:
            query: SQL query to validate.

        Raises:
            ValueError: If query is invalid or too long.
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        if len(query) > MAX_QUERY_LENGTH:
            raise ValueError(f"Query exceeds maximum length of {MAX_QUERY_LENGTH}")

    def _validate_identifier(self, identifier: str) -> bool:
        """Validate SQL identifier (table/column name).

        Args:
            identifier: Identifier to validate.

        Returns:
            True if valid, False otherwise.
        """
        return bool(ALLOWED_IDENTIFIER_PATTERN.match(identifier))

    def analyze_query(self, query: str) -> QueryAnalysis:
        """Analyze a SQL query.

        Args:
            query: SQL query to analyze.

        Returns:
            Query analysis result.

        Raises:
            ValueError: If query is invalid or too long.
        """
        self._validate_query(query)
        query_upper = query.upper().strip()
        query_type = self._detect_query_type(query_upper)

        analysis = QueryAnalysis(
            query=query,
            query_type=query_type,
            tables=self._extract_tables(query),
            columns=self._extract_columns(query),
            has_where="WHERE" in query_upper,
            has_join="JOIN" in query_upper,
            has_subquery="SELECT" in query_upper[7:] if query_upper.startswith("SELECT") else False,
            has_order_by="ORDER BY" in query_upper,
            has_limit="LIMIT" in query_upper,
        )

        # Generate suggestions
        analysis.suggestions = self._generate_suggestions(analysis)
        analysis.index_suggestions = self._generate_index_suggestions(analysis)
        analysis.estimated_cost = self._estimate_cost(analysis)

        return analysis

    def _detect_query_type(self, query: str) -> QueryType:
        """Detect query type.

        Args:
            query: Uppercase query string.

        Returns:
            Query type.
        """
        if query.startswith("SELECT"):
            return QueryType.SELECT
        elif query.startswith("INSERT"):
            return QueryType.INSERT
        elif query.startswith("UPDATE"):
            return QueryType.UPDATE
        elif query.startswith("DELETE"):
            return QueryType.DELETE
        return QueryType.OTHER

    def _extract_tables(self, query: str) -> list[str]:
        """Extract table names from query.

        Args:
            query: SQL query.

        Returns:
            List of table names.
        """
        tables = []

        # FROM clause
        from_match = re.search(r"\bFROM\s+(\w+)", query, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1))

        # JOIN clauses
        join_matches = re.findall(r"\bJOIN\s+(\w+)", query, re.IGNORECASE)
        tables.extend(join_matches)

        # UPDATE/INSERT INTO
        update_match = re.search(r"\bUPDATE\s+(\w+)", query, re.IGNORECASE)
        if update_match:
            tables.append(update_match.group(1))

        insert_match = re.search(r"\bINSERT\s+INTO\s+(\w+)", query, re.IGNORECASE)
        if insert_match:
            tables.append(insert_match.group(1))

        # Filter to valid identifiers only
        return [t for t in set(tables) if self._validate_identifier(t)]

    def _extract_columns(self, query: str) -> list[str]:
        """Extract column names from query.

        Args:
            query: SQL query.

        Returns:
            List of column names.
        """
        columns = []

        # WHERE clause columns
        where_matches = re.findall(r"\bWHERE\s+(\w+)\s*[=<>]", query, re.IGNORECASE)
        columns.extend(where_matches)

        # ORDER BY columns
        order_matches = re.findall(r"\bORDER\s+BY\s+(\w+)", query, re.IGNORECASE)
        columns.extend(order_matches)

        # GROUP BY columns
        group_matches = re.findall(r"\bGROUP\s+BY\s+(\w+)", query, re.IGNORECASE)
        columns.extend(group_matches)

        # Filter to valid identifiers only
        return [c for c in set(columns) if self._validate_identifier(c)]

    def _generate_suggestions(self, analysis: QueryAnalysis) -> list[OptimizationSuggestion]:
        """Generate optimization suggestions.

        Args:
            analysis: Query analysis.

        Returns:
            List of suggestions.
        """
        suggestions = []

        # Check for SELECT *
        if analysis.query_type == QueryType.SELECT and "SELECT *" in analysis.query.upper():
            suggestions.append(OptimizationSuggestion.AVOID_SELECT_STAR)

        # Check for missing LIMIT on SELECT
        if analysis.query_type == QueryType.SELECT and not analysis.has_limit:
            suggestions.append(OptimizationSuggestion.ADD_LIMIT)

        # Check for OR in WHERE (might benefit from UNION)
        if " OR " in analysis.query.upper() and analysis.has_where:
            suggestions.append(OptimizationSuggestion.AVOID_OR)

        # Check for functions on columns in WHERE
        func_pattern = r"\bWHERE\s+\w+\s*\(\s*\w+\s*\)"
        if re.search(func_pattern, analysis.query, re.IGNORECASE):
            suggestions.append(OptimizationSuggestion.AVOID_FUNCTION_ON_COLUMN)

        # Suggest index for WHERE columns without existing index
        if analysis.has_where and analysis.columns:
            suggestions.append(OptimizationSuggestion.ADD_INDEX)

        return suggestions

    def _generate_index_suggestions(self, analysis: QueryAnalysis) -> list[IndexSuggestion]:
        """Generate index suggestions.

        Args:
            analysis: Query analysis.

        Returns:
            List of index suggestions.
        """
        suggestions = []

        if not analysis.tables or not analysis.columns:
            return suggestions

        # Suggest index on WHERE columns
        if analysis.has_where:
            for table in analysis.tables:
                suggestions.append(IndexSuggestion(
                    table=table,
                    columns=analysis.columns[:3],  # Limit to 3 columns
                    index_type="btree",
                    reason="Columns used in WHERE clause",
                    estimated_improvement=30.0,
                ))

        # Suggest covering index for SELECT with specific columns
        if analysis.query_type == QueryType.SELECT and not "SELECT *" in analysis.query.upper():
            select_cols = self._extract_select_columns(analysis.query)
            if select_cols and analysis.tables:
                suggestions.append(IndexSuggestion(
                    table=analysis.tables[0],
                    columns=select_cols[:5],
                    index_type="btree",
                    reason="Covering index for SELECT columns",
                    estimated_improvement=20.0,
                ))

        return suggestions

    def _extract_select_columns(self, query: str) -> list[str]:
        """Extract columns from SELECT clause.

        Args:
            query: SQL query.

        Returns:
            List of column names.
        """
        match = re.search(r"SELECT\s+(.+?)\s+FROM", query, re.IGNORECASE | re.DOTALL)
        if not match:
            return []

        cols_str = match.group(1)
        if "*" in cols_str:
            return []

        # Simple column extraction (doesn't handle complex expressions)
        cols = [c.strip().split(".")[-1] for c in cols_str.split(",")]
        return [c for c in cols if c and not "(" in c]

    def _estimate_cost(self, analysis: QueryAnalysis) -> float:
        """Estimate query cost.

        Args:
            analysis: Query analysis.

        Returns:
            Estimated cost (arbitrary units).
        """
        cost = 1.0

        # Base cost by query type
        type_costs = {
            QueryType.SELECT: 1.0,
            QueryType.INSERT: 2.0,
            QueryType.UPDATE: 3.0,
            QueryType.DELETE: 3.0,
            QueryType.OTHER: 1.0,
        }
        cost *= type_costs.get(analysis.query_type, 1.0)

        # Increase for missing WHERE on UPDATE/DELETE
        if analysis.query_type in (QueryType.UPDATE, QueryType.DELETE) and not analysis.has_where:
            cost *= 10.0

        # Increase for JOINs
        if analysis.has_join:
            cost *= 2.0

        # Increase for subqueries
        if analysis.has_subquery:
            cost *= 3.0

        # Decrease for LIMIT
        if analysis.has_limit:
            cost *= 0.5

        return cost

    def record_query(self, metrics: QueryMetrics) -> None:
        """Record query execution metrics.

        Args:
            metrics: Query metrics.
        """
        self._queries.append(metrics)

        # Trim if over limit
        if len(self._queries) > self._config.max_queries_stored:
            self._queries.pop(0)

        # Track slow queries
        if metrics.execution_time_ms >= self._config.slow_query_threshold_ms:
            self._slow_queries.append(metrics)
            if len(self._slow_queries) > self._config.max_queries_stored:
                self._slow_queries.pop(0)

    def get_slow_queries(self, limit: int = 10) -> list[QueryMetrics]:
        """Get slowest queries.

        Args:
            limit: Maximum number to return.

        Returns:
            List of slow queries sorted by execution time.
        """
        sorted_queries = sorted(
            self._slow_queries,
            key=lambda q: q.execution_time_ms,
            reverse=True,
        )
        return sorted_queries[:limit]

    def get_query_stats(self) -> dict[str, Any]:
        """Get query statistics.

        Returns:
            Statistics dictionary.
        """
        if not self._queries:
            return {
                "total_queries": 0,
                "slow_queries": 0,
                "avg_execution_time_ms": 0.0,
                "max_execution_time_ms": 0.0,
                "queries_by_type": {},
            }

        execution_times = [q.execution_time_ms for q in self._queries]
        type_counts: dict[str, int] = {}
        for q in self._queries:
            type_counts[q.query_type.value] = type_counts.get(q.query_type.value, 0) + 1

        return {
            "total_queries": len(self._queries),
            "slow_queries": len(self._slow_queries),
            "avg_execution_time_ms": sum(execution_times) / len(execution_times),
            "max_execution_time_ms": max(execution_times),
            "queries_by_type": type_counts,
        }

    def clear(self) -> None:
        """Clear all recorded queries."""
        self._queries.clear()
        self._slow_queries.clear()
