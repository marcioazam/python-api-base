"""Property-based tests for query analyzer.

**Feature: api-architecture-analysis, Task 12.4: Database Query Optimization**
**Validates: Requirements 2.1, 9.1**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.infrastructure.observability.query_analyzer import (
    AnalyzerConfig,
    IndexSuggestion,
    OptimizationSuggestion,
    QueryAnalysis,
    QueryAnalyzer,
    QueryMetrics,
    QueryType,
)


# =============================================================================
# Strategies
# =============================================================================

@st.composite
def table_name_strategy(draw: st.DrawFn) -> str:
    """Generate valid table names."""
    return draw(st.text(min_size=3, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"))


@st.composite
def column_name_strategy(draw: st.DrawFn) -> str:
    """Generate valid column names."""
    return draw(st.text(min_size=2, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz_"))


@st.composite
def select_query_strategy(draw: st.DrawFn) -> str:
    """Generate SELECT queries."""
    table = draw(table_name_strategy())
    columns = draw(st.one_of(st.just("*"), column_name_strategy()))
    has_where = draw(st.booleans())
    has_limit = draw(st.booleans())

    query = f"SELECT {columns} FROM {table}"

    if has_where:
        col = draw(column_name_strategy())
        query += f" WHERE {col} = 1"

    if has_limit:
        limit = draw(st.integers(min_value=1, max_value=100))
        query += f" LIMIT {limit}"

    return query


# =============================================================================
# Property Tests - Query Type Detection
# =============================================================================

class TestQueryTypeDetectionProperties:
    """Property tests for query type detection."""

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_select_detected(self, table: str) -> None:
        """**Property 1: SELECT queries are detected**

        *For any* SELECT query, type should be SELECT.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table}"
        analysis = analyzer.analyze_query(query)

        assert analysis.query_type == QueryType.SELECT

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_insert_detected(self, table: str) -> None:
        """**Property 2: INSERT queries are detected**

        *For any* INSERT query, type should be INSERT.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"INSERT INTO {table} (col) VALUES (1)"
        analysis = analyzer.analyze_query(query)

        assert analysis.query_type == QueryType.INSERT

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_update_detected(self, table: str) -> None:
        """**Property 3: UPDATE queries are detected**

        *For any* UPDATE query, type should be UPDATE.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"UPDATE {table} SET col = 1"
        analysis = analyzer.analyze_query(query)

        assert analysis.query_type == QueryType.UPDATE

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_delete_detected(self, table: str) -> None:
        """**Property 4: DELETE queries are detected**

        *For any* DELETE query, type should be DELETE.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"DELETE FROM {table}"
        analysis = analyzer.analyze_query(query)

        assert analysis.query_type == QueryType.DELETE


# =============================================================================
# Property Tests - Table Extraction
# =============================================================================

class TestTableExtractionProperties:
    """Property tests for table extraction."""

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_from_table_extracted(self, table: str) -> None:
        """**Property 5: FROM table is extracted**

        *For any* query with FROM, table should be extracted.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table}"
        analysis = analyzer.analyze_query(query)

        assert table in analysis.tables

    @given(
        table1=table_name_strategy(),
        table2=table_name_strategy(),
    )
    @settings(max_examples=100)
    def test_join_tables_extracted(self, table1: str, table2: str) -> None:
        """**Property 6: JOIN tables are extracted**

        *For any* query with JOIN, both tables should be extracted.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table1} JOIN {table2} ON {table1}.id = {table2}.id"
        analysis = analyzer.analyze_query(query)

        assert table1 in analysis.tables
        assert table2 in analysis.tables


# =============================================================================
# Property Tests - Clause Detection
# =============================================================================

class TestClauseDetectionProperties:
    """Property tests for clause detection."""

    @given(table=table_name_strategy(), column=column_name_strategy())
    @settings(max_examples=100)
    def test_where_detected(self, table: str, column: str) -> None:
        """**Property 7: WHERE clause is detected**

        *For any* query with WHERE, has_where should be True.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table} WHERE {column} = 1"
        analysis = analyzer.analyze_query(query)

        assert analysis.has_where is True

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_no_where_detected(self, table: str) -> None:
        """**Property 8: Missing WHERE is detected**

        *For any* query without WHERE, has_where should be False.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table}"
        analysis = analyzer.analyze_query(query)

        assert analysis.has_where is False

    @given(table=table_name_strategy(), column=column_name_strategy())
    @settings(max_examples=100)
    def test_order_by_detected(self, table: str, column: str) -> None:
        """**Property 9: ORDER BY is detected**

        *For any* query with ORDER BY, has_order_by should be True.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table} ORDER BY {column}"
        analysis = analyzer.analyze_query(query)

        assert analysis.has_order_by is True

    @given(table=table_name_strategy(), limit=st.integers(min_value=1, max_value=100))
    @settings(max_examples=100)
    def test_limit_detected(self, table: str, limit: int) -> None:
        """**Property 10: LIMIT is detected**

        *For any* query with LIMIT, has_limit should be True.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table} LIMIT {limit}"
        analysis = analyzer.analyze_query(query)

        assert analysis.has_limit is True


# =============================================================================
# Property Tests - Optimization Suggestions
# =============================================================================

class TestOptimizationSuggestionProperties:
    """Property tests for optimization suggestions."""

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_select_star_suggestion(self, table: str) -> None:
        """**Property 11: SELECT * triggers suggestion**

        *For any* SELECT * query, should suggest avoiding it.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table}"
        analysis = analyzer.analyze_query(query)

        assert OptimizationSuggestion.AVOID_SELECT_STAR in analysis.suggestions

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_missing_limit_suggestion(self, table: str) -> None:
        """**Property 12: Missing LIMIT triggers suggestion**

        *For any* SELECT without LIMIT, should suggest adding it.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table}"
        analysis = analyzer.analyze_query(query)

        assert OptimizationSuggestion.ADD_LIMIT in analysis.suggestions

    @given(table=table_name_strategy(), column=column_name_strategy())
    @settings(max_examples=100)
    def test_where_suggests_index(self, table: str, column: str) -> None:
        """**Property 13: WHERE clause suggests index**

        *For any* query with WHERE, should suggest adding index.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table} WHERE {column} = 1"
        analysis = analyzer.analyze_query(query)

        assert OptimizationSuggestion.ADD_INDEX in analysis.suggestions


# =============================================================================
# Property Tests - Index Suggestions
# =============================================================================

class TestIndexSuggestionProperties:
    """Property tests for index suggestions."""

    @given(table=table_name_strategy(), column=column_name_strategy())
    @settings(max_examples=100)
    def test_index_suggestion_for_where(self, table: str, column: str) -> None:
        """**Property 14: Index suggested for WHERE columns**

        *For any* query with WHERE, should suggest index on that column.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table} WHERE {column} = 1"
        analysis = analyzer.analyze_query(query)

        assert len(analysis.index_suggestions) > 0
        assert any(s.table == table for s in analysis.index_suggestions)

    @given(
        table=table_name_strategy(),
        columns=st.lists(column_name_strategy(), min_size=1, max_size=3),
    )
    @settings(max_examples=50)
    def test_index_suggestion_has_columns(self, table: str, columns: list[str]) -> None:
        """**Property 15: Index suggestion includes columns**

        *For any* index suggestion, it should have columns.

        **Validates: Requirements 2.1, 9.1**
        """
        suggestion = IndexSuggestion(
            table=table,
            columns=columns,
            reason="Test",
        )

        assert suggestion.table == table
        assert suggestion.columns == columns
        assert suggestion.index_type == "btree"


# =============================================================================
# Property Tests - Query Metrics
# =============================================================================

class TestQueryMetricsProperties:
    """Property tests for query metrics."""

    @given(
        execution_time=st.floats(min_value=0.1, max_value=10000.0),
        rows_examined=st.integers(min_value=0, max_value=1000000),
    )
    @settings(max_examples=100)
    def test_metrics_preserve_values(
        self,
        execution_time: float,
        rows_examined: int,
    ) -> None:
        """**Property 16: Metrics preserve values**

        *For any* metrics values, they should be preserved.

        **Validates: Requirements 2.1, 9.1**
        """
        metrics = QueryMetrics(
            query="SELECT 1",
            query_type=QueryType.SELECT,
            execution_time_ms=execution_time,
            rows_examined=rows_examined,
        )

        assert metrics.execution_time_ms == execution_time
        assert metrics.rows_examined == rows_examined

    @given(threshold=st.floats(min_value=10.0, max_value=1000.0))
    @settings(max_examples=50)
    def test_slow_query_detection(self, threshold: float) -> None:
        """**Property 17: Slow queries are detected**

        *For any* threshold, queries above it should be marked slow.

        **Validates: Requirements 2.1, 9.1**
        """
        config = AnalyzerConfig(slow_query_threshold_ms=threshold)
        analyzer = QueryAnalyzer(config)

        # Record a slow query
        metrics = QueryMetrics(
            query="SELECT 1",
            query_type=QueryType.SELECT,
            execution_time_ms=threshold + 10,
        )
        analyzer.record_query(metrics)

        slow_queries = analyzer.get_slow_queries()
        assert len(slow_queries) == 1


# =============================================================================
# Property Tests - Query Statistics
# =============================================================================

class TestQueryStatsProperties:
    """Property tests for query statistics."""

    def test_empty_stats(self) -> None:
        """**Property 18: Empty analyzer has zero stats**

        New analyzer should have zero statistics.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        stats = analyzer.get_query_stats()

        assert stats["total_queries"] == 0
        assert stats["slow_queries"] == 0
        assert stats["avg_execution_time_ms"] == 0.0

    @given(num_queries=st.integers(min_value=1, max_value=20))
    @settings(max_examples=50)
    def test_stats_count_queries(self, num_queries: int) -> None:
        """**Property 19: Stats count all queries**

        *For any* number of recorded queries, stats should reflect count.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()

        for i in range(num_queries):
            metrics = QueryMetrics(
                query=f"SELECT {i}",
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
            )
            analyzer.record_query(metrics)

        stats = analyzer.get_query_stats()
        assert stats["total_queries"] == num_queries

    def test_clear_removes_all(self) -> None:
        """**Property 20: Clear removes all queries**

        Clearing should remove all recorded queries.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()

        for i in range(5):
            metrics = QueryMetrics(
                query=f"SELECT {i}",
                query_type=QueryType.SELECT,
                execution_time_ms=10.0,
            )
            analyzer.record_query(metrics)

        analyzer.clear()
        stats = analyzer.get_query_stats()

        assert stats["total_queries"] == 0


# =============================================================================
# Property Tests - Cost Estimation
# =============================================================================

class TestCostEstimationProperties:
    """Property tests for cost estimation."""

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_select_has_base_cost(self, table: str) -> None:
        """**Property 21: SELECT has base cost**

        *For any* SELECT query, cost should be positive.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()
        query = f"SELECT * FROM {table}"
        analysis = analyzer.analyze_query(query)

        assert analysis.estimated_cost > 0

    @given(table=table_name_strategy())
    @settings(max_examples=100)
    def test_limit_reduces_cost(self, table: str) -> None:
        """**Property 22: LIMIT reduces estimated cost**

        *For any* query, adding LIMIT should reduce cost.

        **Validates: Requirements 2.1, 9.1**
        """
        analyzer = QueryAnalyzer()

        query_no_limit = f"SELECT * FROM {table}"
        query_with_limit = f"SELECT * FROM {table} LIMIT 10"

        analysis_no_limit = analyzer.analyze_query(query_no_limit)
        analysis_with_limit = analyzer.analyze_query(query_with_limit)

        assert analysis_with_limit.estimated_cost < analysis_no_limit.estimated_cost
