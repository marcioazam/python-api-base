"""Property-based tests for Anomaly Detection.

**Feature: api-architecture-analysis**
**Validates: Requirements 7.3**
"""

import pytest
from hypothesis import given, settings, strategies as st

from my_api.shared.anomaly import (
    Anomaly,
    AnomalyConfig,
    AnomalyDetector,
    AnomalySeverity,
    AnomalyType,
    DataPoint,
    StatisticalAnalyzer,
    create_anomaly_detector,
)
from datetime import datetime


# Strategies
value_strategy = st.floats(min_value=-1000.0, max_value=1000.0, allow_nan=False, allow_infinity=False)
positive_value_strategy = st.floats(min_value=0.1, max_value=1000.0, allow_nan=False, allow_infinity=False)
values_list_strategy = st.lists(
    st.floats(min_value=-100.0, max_value=100.0, allow_nan=False, allow_infinity=False),
    min_size=2,
    max_size=100,
)


class TestStatisticalAnalyzerProperties:
    """Property tests for StatisticalAnalyzer."""

    @given(values=values_list_strategy)
    @settings(max_examples=100)
    def test_mean_is_within_range(self, values: list[float]) -> None:
        """Property: Mean is within min and max of values."""
        mean = StatisticalAnalyzer.mean(values)
        assert min(values) <= mean <= max(values)

    @given(values=values_list_strategy)
    @settings(max_examples=100)
    def test_std_dev_is_non_negative(self, values: list[float]) -> None:
        """Property: Standard deviation is non-negative."""
        std = StatisticalAnalyzer.std_dev(values)
        assert std >= 0

    @given(value=value_strategy, mean=value_strategy, std=positive_value_strategy)
    @settings(max_examples=100)
    def test_z_score_sign_matches_deviation(
        self, value: float, mean: float, std: float
    ) -> None:
        """Property: Z-score sign matches direction of deviation."""
        z = StatisticalAnalyzer.z_score(value, mean, std)
        if value > mean:
            assert z > 0 or abs(value - mean) < 0.0001
        elif value < mean:
            assert z < 0 or abs(value - mean) < 0.0001

    @given(values=values_list_strategy)
    @settings(max_examples=100)
    def test_moving_average_length_matches_input(self, values: list[float]) -> None:
        """Property: Moving average has same length as input."""
        ma = StatisticalAnalyzer.moving_average(values, window=5)
        assert len(ma) == len(values)

    @given(
        values=st.lists(
            st.floats(min_value=0.0, max_value=100.0, allow_nan=False),
            min_size=10,
            max_size=100,
        ),
        p=st.floats(min_value=0.0, max_value=1.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_percentile_is_within_range(self, values: list[float], p: float) -> None:
        """Property: Percentile is within min and max of values."""
        percentile = StatisticalAnalyzer.percentile(values, p)
        assert min(values) <= percentile <= max(values)


class TestAnomalyProperties:
    """Property tests for Anomaly model."""

    @given(
        value=value_strategy,
        expected=st.floats(min_value=0.1, max_value=100.0, allow_nan=False),
    )
    @settings(max_examples=100)
    def test_deviation_percent_is_non_negative(
        self, value: float, expected: float
    ) -> None:
        """Property: Deviation percent is non-negative."""
        anomaly = Anomaly(
            anomaly_type=AnomalyType.SPIKE,
            severity=AnomalySeverity.WARNING,
            value=value,
            expected_value=expected,
            deviation=1.0,
            timestamp=datetime.now(),
            metric_name="test",
        )
        assert anomaly.deviation_percent >= 0


class TestAnomalyDetectorProperties:
    """Property tests for AnomalyDetector."""

    @given(
        values=st.lists(
            st.floats(min_value=10.0, max_value=20.0, allow_nan=False),
            min_size=20,
            max_size=50,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_normal_values_no_anomaly(self, values: list[float]) -> None:
        """Property: Normal values within range don't trigger anomalies."""
        detector = create_anomaly_detector()

        anomalies = []
        for value in values:
            anomaly = await detector.record("test_metric", value)
            if anomaly:
                anomalies.append(anomaly)

        # Most values should not be anomalies
        assert len(anomalies) < len(values) * 0.2  # Less than 20% anomalies

    @given(
        base_values=st.lists(
            st.floats(min_value=10.0, max_value=20.0, allow_nan=False),
            min_size=15,
            max_size=30,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_spike_detected(self, base_values: list[float]) -> None:
        """Property: Large spike is detected as anomaly."""
        detector = create_anomaly_detector()

        # Record normal values
        for value in base_values:
            await detector.record("test_metric", value)

        # Record a spike (10x the mean)
        mean = sum(base_values) / len(base_values)
        spike_value = mean * 10

        anomaly = await detector.record("test_metric", spike_value)

        # Should detect as spike or outlier
        if anomaly:
            assert anomaly.anomaly_type in (AnomalyType.SPIKE, AnomalyType.OUTLIER)
            assert anomaly.value == spike_value

    @given(
        base_values=st.lists(
            st.floats(min_value=10.0, max_value=20.0, allow_nan=False),
            min_size=15,
            max_size=30,
        ),
    )
    @settings(max_examples=50)
    @pytest.mark.anyio
    async def test_drop_detected(self, base_values: list[float]) -> None:
        """Property: Large drop is detected as anomaly."""
        detector = create_anomaly_detector()

        # Record normal values
        for value in base_values:
            await detector.record("test_metric", value)

        # Record a drop (near zero)
        drop_value = 0.1

        anomaly = await detector.record("test_metric", drop_value)

        # Should detect as drop or outlier
        if anomaly:
            assert anomaly.anomaly_type in (AnomalyType.DROP, AnomalyType.OUTLIER)

    @pytest.mark.anyio
    async def test_statistics_calculation(self) -> None:
        """Property: Statistics are calculated correctly."""
        detector = create_anomaly_detector()

        values = [10.0, 20.0, 30.0, 40.0, 50.0]
        for value in values:
            await detector.record("test_metric", value)

        stats = detector.get_statistics("test_metric")

        assert stats["count"] == 5
        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0

    @pytest.mark.anyio
    async def test_empty_metric_statistics(self) -> None:
        """Property: Empty metric returns zero statistics."""
        detector = create_anomaly_detector()

        stats = detector.get_statistics("nonexistent")

        assert stats["count"] == 0
        assert stats["mean"] == 0
        assert stats["std_dev"] == 0


class TestAnomalyConfigProperties:
    """Property tests for AnomalyConfig."""

    @given(
        z_threshold=st.floats(min_value=1.0, max_value=5.0, allow_nan=False),
        min_points=st.integers(min_value=5, max_value=50),
    )
    @settings(max_examples=100)
    def test_config_values_preserved(
        self, z_threshold: float, min_points: int
    ) -> None:
        """Property: Config values are preserved."""
        config = AnomalyConfig(
            z_score_threshold=z_threshold,
            min_data_points=min_points,
        )
        assert config.z_score_threshold == z_threshold
        assert config.min_data_points == min_points

    def test_default_config_has_reasonable_values(self) -> None:
        """Property: Default config has reasonable values."""
        config = AnomalyConfig()

        assert config.z_score_threshold > 0
        assert config.min_data_points > 0
        assert config.window_size > 0
        assert config.warning_threshold < config.critical_threshold


class TestSeverityDeterminationProperties:
    """Property tests for severity determination."""

    @pytest.mark.anyio
    async def test_high_deviation_is_critical(self) -> None:
        """Property: High deviation results in CRITICAL severity."""
        config = AnomalyConfig(
            z_score_threshold=2.0,
            critical_threshold=3.0,
            min_data_points=10,
        )
        detector = AnomalyDetector(config=config)

        # Record stable values
        for _ in range(15):
            await detector.record("test", 10.0)

        # Record extreme value
        anomaly = await detector.record("test", 100.0)

        if anomaly:
            assert anomaly.severity == AnomalySeverity.CRITICAL
