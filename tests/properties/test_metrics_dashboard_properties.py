"""Property-based tests for Metrics Dashboard.

**Feature: api-architecture-analysis**
**Validates: Requirements 7.3**
"""

import json
from datetime import datetime, timedelta

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.metrics_dashboard import (
    ChartType,
    Dashboard,
    DashboardBuilder,
    DashboardData,
    InMemoryMetricsStore,
    MetricPoint,
    MetricSeries,
    MetricType,
    MetricsDashboard,
    TimeRange,
    Widget,
    create_metrics_dashboard,
    create_performance_dashboard,
)


# Strategies
metric_name_strategy = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N", "P")),
    min_size=1,
    max_size=50,
).filter(lambda x: x.strip())

metric_value_strategy = st.floats(
    min_value=0.0,
    max_value=10000.0,
    allow_nan=False,
    allow_infinity=False,
)

time_range_strategy = st.sampled_from(list(TimeRange))
chart_type_strategy = st.sampled_from(list(ChartType))
metric_type_strategy = st.sampled_from(list(MetricType))


class TestMetricPointProperties:
    """Property tests for MetricPoint."""

    @given(value=metric_value_strategy)
    @settings(max_examples=100)
    def test_metric_point_preserves_value(self, value: float) -> None:
        """Property: MetricPoint preserves the value."""
        point = MetricPoint(
            timestamp=datetime.now(),
            value=value,
        )
        assert point.value == value

    def test_metric_point_is_frozen(self) -> None:
        """Property: MetricPoint is immutable."""
        point = MetricPoint(
            timestamp=datetime.now(),
            value=42.0,
        )
        with pytest.raises(Exception):
            point.value = 100.0  # type: ignore


class TestMetricSeriesProperties:
    """Property tests for MetricSeries."""

    @given(
        name=metric_name_strategy,
        metric_type=metric_type_strategy,
        value=metric_value_strategy,
    )
    @settings(max_examples=100)
    def test_add_point_increases_length(
        self, name: str, metric_type: MetricType, value: float
    ) -> None:
        """Property: Adding points increases series length."""
        series = MetricSeries(name=name, metric_type=metric_type)
        initial_len = len(series.points)
        series.add_point(value)
        assert len(series.points) == initial_len + 1

    @given(
        name=metric_name_strategy,
        values=st.lists(metric_value_strategy, min_size=1, max_size=10),
    )
    @settings(max_examples=100)
    def test_get_latest_returns_last_point(
        self, name: str, values: list[float]
    ) -> None:
        """Property: get_latest returns the most recent point."""
        series = MetricSeries(name=name, metric_type=MetricType.GAUGE)
        for value in values:
            series.add_point(value)

        latest = series.get_latest()
        assert latest is not None
        assert latest.value == values[-1]

    @given(
        name=metric_name_strategy,
        time_range=time_range_strategy,
    )
    @settings(max_examples=100)
    def test_get_range_filters_by_time(
        self, name: str, time_range: TimeRange
    ) -> None:
        """Property: get_range returns points within time range."""
        series = MetricSeries(name=name, metric_type=MetricType.GAUGE)

        # Add old point
        old_time = datetime.now() - time_range.to_timedelta() - timedelta(minutes=1)
        old_point = MetricPoint(timestamp=old_time, value=1.0)
        series.points.append(old_point)

        # Add recent point
        series.add_point(2.0)

        recent_points = series.get_range(time_range)
        assert len(recent_points) == 1
        assert recent_points[0].value == 2.0



class TestWidgetProperties:
    """Property tests for Widget."""

    @given(
        widget_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        title=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        chart_type=chart_type_strategy,
        metrics=st.lists(metric_name_strategy, min_size=1, max_size=5),
    )
    @settings(max_examples=100)
    def test_widget_preserves_configuration(
        self,
        widget_id: str,
        title: str,
        chart_type: ChartType,
        metrics: list[str],
    ) -> None:
        """Property: Widget preserves configuration."""
        widget = Widget(
            id=widget_id,
            title=title,
            chart_type=chart_type,
            metric_names=metrics,
        )
        assert widget.id == widget_id
        assert widget.title == title
        assert widget.chart_type == chart_type
        assert widget.metric_names == metrics


class TestDashboardProperties:
    """Property tests for Dashboard."""

    @given(
        dashboard_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        title=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100)
    def test_dashboard_starts_empty(
        self, dashboard_id: str, title: str
    ) -> None:
        """Property: New dashboard starts with no widgets."""
        dashboard = Dashboard(id=dashboard_id, title=title)
        assert len(dashboard.widgets) == 0

    @given(
        dashboard_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        title=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
        widget_count=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=50)
    def test_add_widget_increases_count(
        self, dashboard_id: str, title: str, widget_count: int
    ) -> None:
        """Property: Adding widgets increases widget count."""
        dashboard = Dashboard(id=dashboard_id, title=title)

        for i in range(widget_count):
            widget = Widget(
                id=f"widget_{i}",
                title=f"Widget {i}",
                chart_type=ChartType.LINE,
                metric_names=["test_metric"],
            )
            dashboard.add_widget(widget)

        assert len(dashboard.widgets) == widget_count

    def test_remove_widget_decreases_count(self) -> None:
        """Property: Removing widget decreases count."""
        dashboard = Dashboard(id="test", title="Test")
        widget = Widget(
            id="test_widget",
            title="Test Widget",
            chart_type=ChartType.LINE,
            metric_names=["test"],
        )
        dashboard.add_widget(widget)

        assert len(dashboard.widgets) == 1
        removed = dashboard.remove_widget("test_widget")
        assert removed is True
        assert len(dashboard.widgets) == 0

    def test_remove_nonexistent_widget_returns_false(self) -> None:
        """Property: Removing nonexistent widget returns False."""
        dashboard = Dashboard(id="test", title="Test")
        removed = dashboard.remove_widget("nonexistent")
        assert removed is False


class TestInMemoryMetricsStoreProperties:
    """Property tests for InMemoryMetricsStore."""

    @given(
        name=metric_name_strategy,
        value=metric_value_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_store_and_retrieve_metric(
        self, name: str, value: float
    ) -> None:
        """Property: Stored metrics can be retrieved."""
        store = InMemoryMetricsStore()
        series = MetricSeries(
            name=name,
            metric_type=MetricType.GAUGE,
            points=[MetricPoint(timestamp=datetime.now(), value=value)],
        )

        await store.store_metric(series)
        retrieved = await store.get_metric(name)

        assert retrieved is not None
        assert retrieved.name == name
        assert len(retrieved.points) >= 1

    @given(
        names=st.lists(metric_name_strategy, min_size=1, max_size=5, unique=True),
    )
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_list_metrics_returns_stored_names(
        self, names: list[str]
    ) -> None:
        """Property: list_metrics returns names of stored metrics."""
        store = InMemoryMetricsStore()

        for name in names:
            series = MetricSeries(
                name=name,
                metric_type=MetricType.GAUGE,
                points=[MetricPoint(timestamp=datetime.now(), value=1.0)],
            )
            await store.store_metric(series)

        stored_names = await store.list_metrics()
        for name in names:
            assert name in stored_names

    def test_record_value_creates_series(self) -> None:
        """Property: record_value creates series if not exists."""
        store = InMemoryMetricsStore()
        store.record_value("test_metric", 42.0)

        assert "test_metric" in store._metrics
        series = store._metrics["test_metric"]
        assert len(series.points) == 1
        assert series.points[0].value == 42.0

    def test_max_points_limit_enforced(self) -> None:
        """Property: Store respects max points limit."""
        max_points = 5
        store = InMemoryMetricsStore(max_points_per_series=max_points)

        for i in range(max_points + 3):
            store.record_value("test", float(i))

        series = store._metrics["test"]
        assert len(series.points) <= max_points



class TestMetricsDashboardProperties:
    """Property tests for MetricsDashboard."""

    @pytest.mark.anyio
    async def test_default_dashboard_exists(self) -> None:
        """Property: Dashboard always has a default system dashboard."""
        dashboard_service = create_metrics_dashboard()

        system_dashboard = dashboard_service.get_dashboard("system")
        assert system_dashboard is not None
        assert system_dashboard.id == "system"
        assert len(system_dashboard.widgets) > 0

    @given(
        name=metric_name_strategy,
        value=metric_value_strategy,
        metric_type=metric_type_strategy,
    )
    @settings(max_examples=100)
    @pytest.mark.anyio
    async def test_record_metric_stores_data(
        self, name: str, value: float, metric_type: MetricType
    ) -> None:
        """Property: Recorded metrics are stored."""
        dashboard_service = create_metrics_dashboard()

        await dashboard_service.record_metric(name, value, metric_type)

        stored_metric = await dashboard_service._store.get_metric(name)
        assert stored_metric is not None
        assert stored_metric.name == name
        assert len(stored_metric.points) >= 1

    @pytest.mark.anyio
    async def test_get_dashboard_data_returns_valid_structure(self) -> None:
        """Property: Dashboard data has valid structure."""
        dashboard_service = create_metrics_dashboard()

        await dashboard_service.record_metric("http_requests_total", 100.0)
        await dashboard_service.record_metric("http_request_duration_p95", 250.0)

        data = await dashboard_service.get_dashboard_data("system")
        assert data is not None
        assert data.dashboard.id == "system"
        assert isinstance(data.widget_data, dict)
        assert data.timestamp is not None

    def test_create_dashboard_adds_to_collection(self) -> None:
        """Property: Created dashboards are added to collection."""
        dashboard_service = create_metrics_dashboard()

        custom_dashboard = Dashboard(id="custom", title="Custom Dashboard")
        dashboard_service.create_dashboard(custom_dashboard)

        retrieved = dashboard_service.get_dashboard("custom")
        assert retrieved is not None
        assert retrieved.id == "custom"

    def test_list_dashboards_includes_all(self) -> None:
        """Property: list_dashboards includes all created dashboards."""
        dashboard_service = create_metrics_dashboard()

        initial_count = len(dashboard_service.list_dashboards())

        custom_dashboard = Dashboard(id="test", title="Test")
        dashboard_service.create_dashboard(custom_dashboard)

        all_dashboards = dashboard_service.list_dashboards()
        assert len(all_dashboards) == initial_count + 1
        assert any(d.id == "test" for d in all_dashboards)

    def test_cannot_delete_system_dashboard(self) -> None:
        """Property: System dashboard cannot be deleted."""
        dashboard_service = create_metrics_dashboard()

        deleted = dashboard_service.delete_dashboard("system")
        assert deleted is False

        system_dashboard = dashboard_service.get_dashboard("system")
        assert system_dashboard is not None


class TestDashboardBuilderProperties:
    """Property tests for DashboardBuilder."""

    @given(
        dashboard_id=st.text(min_size=1, max_size=20).filter(lambda x: x.strip()),
        title=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    )
    @settings(max_examples=100)
    def test_builder_creates_dashboard_with_id_and_title(
        self, dashboard_id: str, title: str
    ) -> None:
        """Property: Builder creates dashboard with correct ID and title."""
        dashboard = DashboardBuilder(dashboard_id, title).build()
        assert dashboard.id == dashboard_id
        assert dashboard.title == title

    def test_builder_fluent_interface(self) -> None:
        """Property: Builder methods return builder for chaining."""
        builder = DashboardBuilder("test", "Test Dashboard")

        result = (
            builder
            .add_line_chart("chart1", "Chart 1", ["metric1"])
            .add_gauge("gauge1", "Gauge 1", "metric2")
            .add_bar_chart("bar1", "Bar 1", ["metric3"])
        )

        assert result is builder
        dashboard = result.build()
        assert len(dashboard.widgets) == 3


class TestTimeRangeProperties:
    """Property tests for TimeRange."""

    @given(time_range=time_range_strategy)
    @settings(max_examples=100)
    def test_to_timedelta_returns_positive_duration(
        self, time_range: TimeRange
    ) -> None:
        """Property: to_timedelta returns positive duration."""
        delta = time_range.to_timedelta()
        assert delta.total_seconds() > 0

    def test_all_time_ranges_have_valid_timedeltas(self) -> None:
        """Property: All time ranges convert to valid timedeltas."""
        for time_range in TimeRange:
            delta = time_range.to_timedelta()
            assert isinstance(delta, timedelta)
            assert delta.total_seconds() > 0


class TestDashboardDataProperties:
    """Property tests for DashboardData."""

    def test_to_json_produces_valid_json(self) -> None:
        """Property: to_json produces valid JSON."""
        dashboard = Dashboard(id="test", title="Test")
        data = {
            "widget1": {"series": [], "chart_type": "line"},
        }

        dd = DashboardData(dashboard=dashboard, widget_data=data)

        json_str = dd.to_json()
        parsed = json.loads(json_str)

        assert "dashboard" in parsed
        assert "data" in parsed
        assert "timestamp" in parsed


class TestPreConfiguredDashboardProperties:
    """Property tests for pre-configured dashboards."""

    def test_performance_dashboard_has_expected_widgets(self) -> None:
        """Property: Performance dashboard has expected widgets."""
        dashboard = create_performance_dashboard()

        assert dashboard.id == "performance"
        assert dashboard.title == "Performance Metrics"
        assert len(dashboard.widgets) > 0

        widget_ids = {w.id for w in dashboard.widgets}
        expected_widgets = {"cpu_usage", "memory_usage", "disk_usage", "top_endpoints"}

        for expected in expected_widgets:
            assert expected in widget_ids
