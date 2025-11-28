"""Property-based tests for Performance Baseline module.

**Feature: api-architecture-analysis, Property 15.3: Performance Regression Testing**
**Validates: Requirements 8.4, 8.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path
from datetime import datetime
import tempfile

from src.my_api.shared.perf_baseline import (
    RegressionSeverity,
    BenchmarkResult,
    BenchmarkStats,
    PerformanceBaseline,
    RegressionResult,
    RegressionConfig,
    BaselineStore,
    RegressionDetector,
    Benchmark,
    BenchmarkSuite,
    ComparisonReport,
    PerformanceTracker,
    benchmark,
)


# Strategies
benchmark_names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_-"),
    min_size=1,
    max_size=30,
)
durations = st.floats(min_value=0.1, max_value=10000.0, allow_nan=False)
memory_sizes = st.integers(min_value=0, max_value=1000000000)
iterations = st.integers(min_value=1, max_value=1000)
percentages = st.floats(min_value=0.0, max_value=200.0, allow_nan=False)
versions = st.from_regex(r"[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True)


class TestBenchmarkResult:
    """Property tests for BenchmarkResult."""

    @given(name=benchmark_names, duration=durations, iters=iterations)
    @settings(max_examples=100)
    def test_duration_per_iteration(
        self, name: str, duration: float, iters: int
    ) -> None:
        """Duration per iteration is total / iterations."""
        result = BenchmarkResult(
            name=name, duration_ms=duration, iterations=iters
        )
        expected = duration / iters
        assert abs(result.duration_per_iteration - expected) < 0.0001

    @given(name=benchmark_names, duration=durations)
    @settings(max_examples=100)
    def test_to_dict_contains_fields(self, name: str, duration: float) -> None:
        """to_dict contains all required fields."""
        result = BenchmarkResult(name=name, duration_ms=duration)
        d = result.to_dict()
        assert "name" in d
        assert "duration_ms" in d
        assert "memory_bytes" in d
        assert "iterations" in d
        assert "timestamp" in d


class TestBenchmarkStats:
    """Property tests for BenchmarkStats."""

    @given(samples=st.lists(durations, min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_mean_calculation(self, samples: list[float]) -> None:
        """Mean is sum / count."""
        stats = BenchmarkStats(name="test", samples=samples)
        expected = sum(samples) / len(samples)
        assert abs(stats.mean - expected) < 0.0001

    @given(samples=st.lists(durations, min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_min_max_bounds(self, samples: list[float]) -> None:
        """Min and max are correct."""
        stats = BenchmarkStats(name="test", samples=samples)
        assert stats.min_value == min(samples)
        assert stats.max_value == max(samples)

    @given(samples=st.lists(durations, min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_count_matches_samples(self, samples: list[float]) -> None:
        """Count matches number of samples."""
        stats = BenchmarkStats(name="test", samples=samples)
        assert stats.count == len(samples)

    @given(samples=st.lists(durations, min_size=1, max_size=100))
    @settings(max_examples=100)
    def test_p95_p99_ordering(self, samples: list[float]) -> None:
        """P95 <= P99."""
        stats = BenchmarkStats(name="test", samples=samples)
        assert stats.p95 <= stats.p99

    @given(name=benchmark_names, sample=durations)
    @settings(max_examples=100)
    def test_add_sample(self, name: str, sample: float) -> None:
        """Adding sample increases count."""
        stats = BenchmarkStats(name=name)
        initial = stats.count
        stats.add_sample(sample)
        assert stats.count == initial + 1

    def test_empty_stats(self) -> None:
        """Empty stats return zero values."""
        stats = BenchmarkStats(name="test")
        assert stats.mean == 0.0
        assert stats.median == 0.0
        assert stats.std_dev == 0.0


class TestPerformanceBaseline:
    """Property tests for PerformanceBaseline."""

    @given(samples=st.lists(durations, min_size=2, max_size=50))
    @settings(max_examples=100)
    def test_from_stats(self, samples: list[float]) -> None:
        """Baseline created from stats has correct values."""
        stats = BenchmarkStats(name="test", samples=samples)
        baseline = PerformanceBaseline.from_stats(stats)
        assert baseline.name == stats.name
        assert abs(baseline.mean_ms - stats.mean) < 0.0001
        assert baseline.sample_count == stats.count

    @given(
        name=benchmark_names,
        mean=durations,
        std_dev=durations,
        p95=durations,
        p99=durations,
    )
    @settings(max_examples=100)
    def test_roundtrip_dict(
        self, name: str, mean: float, std_dev: float, p95: float, p99: float
    ) -> None:
        """Baseline roundtrips through dict."""
        baseline = PerformanceBaseline(
            name=name,
            mean_ms=mean,
            std_dev_ms=std_dev,
            p95_ms=p95,
            p99_ms=p99,
            sample_count=10,
        )
        d = baseline.to_dict()
        restored = PerformanceBaseline.from_dict(d)
        assert restored.name == baseline.name
        assert abs(restored.mean_ms - baseline.mean_ms) < 0.0001


class TestRegressionConfig:
    """Property tests for RegressionConfig."""

    @given(change=percentages)
    @settings(max_examples=100)
    def test_severity_ordering(self, change: float) -> None:
        """Higher change produces higher or equal severity."""
        config = RegressionConfig()
        severity = config.get_severity(change)
        if change < config.minor_threshold_percent:
            assert severity == RegressionSeverity.NONE
        elif change >= config.critical_threshold_percent:
            assert severity == RegressionSeverity.CRITICAL

    @given(
        minor=st.floats(min_value=5.0, max_value=15.0),
        moderate=st.floats(min_value=25.0, max_value=35.0),
        severe=st.floats(min_value=50.0, max_value=70.0),
        critical=st.floats(min_value=90.0, max_value=150.0),
    )
    @settings(max_examples=100)
    def test_custom_thresholds(
        self, minor: float, moderate: float, severe: float, critical: float
    ) -> None:
        """Custom thresholds work correctly."""
        config = RegressionConfig(
            minor_threshold_percent=minor,
            moderate_threshold_percent=moderate,
            severe_threshold_percent=severe,
            critical_threshold_percent=critical,
        )
        assert config.get_severity(minor - 1) == RegressionSeverity.NONE
        assert config.get_severity(minor + 5) == RegressionSeverity.MINOR
        assert config.get_severity(moderate + 5) == RegressionSeverity.MODERATE


class TestBaselineStore:
    """Property tests for BaselineStore."""

    @given(
        name=benchmark_names,
        mean=durations,
    )
    @settings(max_examples=50)
    def test_set_and_get(self, name: str, mean: float) -> None:
        """Set baseline can be retrieved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = BaselineStore(Path(tmpdir) / "baselines.json")
            baseline = PerformanceBaseline(
                name=name,
                mean_ms=mean,
                std_dev_ms=1.0,
                p95_ms=mean * 1.1,
                p99_ms=mean * 1.2,
                sample_count=10,
            )
            store.set(baseline)
            retrieved = store.get(name)
            assert retrieved is not None
            assert retrieved.name == name

    @given(name=benchmark_names)
    @settings(max_examples=50)
    def test_get_nonexistent(self, name: str) -> None:
        """Getting nonexistent baseline returns None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = BaselineStore(Path(tmpdir) / "baselines.json")
            assert store.get(name) is None

    @given(names=st.lists(benchmark_names, min_size=1, max_size=5, unique=True))
    @settings(max_examples=50)
    def test_list_all(self, names: list[str]) -> None:
        """list_all returns all baseline names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = BaselineStore(Path(tmpdir) / "baselines.json")
            for name in names:
                baseline = PerformanceBaseline(
                    name=name,
                    mean_ms=100.0,
                    std_dev_ms=10.0,
                    p95_ms=110.0,
                    p99_ms=120.0,
                    sample_count=10,
                )
                store.set(baseline)
            listed = store.list_all()
            assert set(listed) == set(names)


class TestRegressionDetector:
    """Property tests for RegressionDetector."""

    @given(
        baseline_mean=st.floats(min_value=10.0, max_value=100.0),
        current_mean=st.floats(min_value=10.0, max_value=200.0),
    )
    @settings(max_examples=100)
    def test_analyze_detects_regression(
        self, baseline_mean: float, current_mean: float
    ) -> None:
        """Analyzer detects regressions correctly."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = BaselineStore(Path(tmpdir) / "baselines.json")
            baseline = PerformanceBaseline(
                name="test",
                mean_ms=baseline_mean,
                std_dev_ms=baseline_mean * 0.1,
                p95_ms=baseline_mean * 1.1,
                p99_ms=baseline_mean * 1.2,
                sample_count=10,
            )
            store.set(baseline)
            detector = RegressionDetector(store)
            stats = BenchmarkStats(name="test", samples=[current_mean] * 10)
            result = detector.analyze(stats)
            if current_mean > baseline_mean * 1.1:
                assert result.percent_change > 0

    @given(name=benchmark_names)
    @settings(max_examples=50)
    def test_no_baseline_no_regression(self, name: str) -> None:
        """No baseline means no regression detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            store = BaselineStore(Path(tmpdir) / "baselines.json")
            detector = RegressionDetector(store)
            stats = BenchmarkStats(name=name, samples=[100.0] * 10)
            result = detector.analyze(stats)
            assert result.severity == RegressionSeverity.NONE


class TestBenchmark:
    """Property tests for Benchmark."""

    @given(
        name=benchmark_names,
        warmup=st.integers(min_value=0, max_value=5),
        iters=st.integers(min_value=1, max_value=10),
    )
    @settings(max_examples=50, deadline=None)
    def test_run_produces_stats(
        self, name: str, warmup: int, iters: int
    ) -> None:
        """Running benchmark produces stats."""
        bench = Benchmark(name, warmup, iters)
        stats = bench.run(lambda: None)
        assert stats.name == name
        assert stats.count == iters

    @given(name=benchmark_names)
    @settings(max_examples=50, deadline=None)
    def test_stats_property(self, name: str) -> None:
        """Stats property returns benchmark stats."""
        bench = Benchmark(name)
        bench.run(lambda: None)
        assert bench.stats.name == name


class TestBenchmarkSuite:
    """Property tests for BenchmarkSuite."""

    @given(
        suite_name=benchmark_names,
        bench_names=st.lists(benchmark_names, min_size=1, max_size=3, unique=True),
    )
    @settings(max_examples=30, deadline=None)
    def test_run_all(self, suite_name: str, bench_names: list[str]) -> None:
        """Running suite produces results for all benchmarks."""
        suite = BenchmarkSuite(suite_name)
        for name in bench_names:
            suite.add(name, lambda: None)
        results = suite.run_all(warmup=1, iterations=3)
        assert len(results) == len(bench_names)
        for name in bench_names:
            assert name in results


class TestComparisonReport:
    """Property tests for ComparisonReport."""

    @given(
        regression_count=st.integers(min_value=0, max_value=5),
        improvement_count=st.integers(min_value=0, max_value=5),
    )
    @settings(max_examples=100)
    def test_has_regressions(
        self, regression_count: int, improvement_count: int
    ) -> None:
        """has_regressions reflects regression count."""
        report = ComparisonReport()
        for i in range(regression_count):
            baseline = PerformanceBaseline(
                name=f"test{i}",
                mean_ms=100.0,
                std_dev_ms=10.0,
                p95_ms=110.0,
                p99_ms=120.0,
                sample_count=10,
            )
            stats = BenchmarkStats(name=f"test{i}", samples=[150.0] * 10)
            result = RegressionResult(
                benchmark_name=f"test{i}",
                baseline=baseline,
                current_stats=stats,
                severity=RegressionSeverity.MODERATE,
                percent_change=50.0,
                message="test",
            )
            report.regressions.append(result)
        assert report.has_regressions == (regression_count > 0)

    def test_to_json_valid(self) -> None:
        """to_json produces valid JSON."""
        report = ComparisonReport()
        json_str = report.to_json()
        import json
        parsed = json.loads(json_str)
        assert "timestamp" in parsed
        assert "regressions" in parsed

    def test_generate_summary(self) -> None:
        """Summary generation works."""
        report = ComparisonReport()
        summary = report.generate_summary()
        assert "Performance Comparison Report" in summary


class TestPerformanceTracker:
    """Property tests for PerformanceTracker."""

    @given(samples=st.lists(durations, min_size=2, max_size=20))
    @settings(max_examples=50)
    def test_update_and_check(self, samples: list[float]) -> None:
        """Update baseline then check regression."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "baselines.json")
            stats = BenchmarkStats(name="test", samples=samples)
            tracker.update_baseline(stats)
            result = tracker.check_regression(stats)
            assert result.severity == RegressionSeverity.NONE

    @given(names=st.lists(benchmark_names, min_size=1, max_size=3, unique=True))
    @settings(max_examples=30)
    def test_list_baselines(self, names: list[str]) -> None:
        """List baselines returns all names."""
        with tempfile.TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(Path(tmpdir) / "baselines.json")
            for name in names:
                stats = BenchmarkStats(name=name, samples=[100.0] * 10)
                tracker.update_baseline(stats)
            listed = tracker.list_baselines()
            assert set(listed) == set(names)


class TestBenchmarkDecorator:
    """Property tests for benchmark decorator."""

    @given(name=benchmark_names)
    @settings(max_examples=30, deadline=None)
    def test_decorator_returns_stats(self, name: str) -> None:
        """Decorator returns stats when called."""
        @benchmark(name, warmup=1, iterations=3)
        def test_func() -> int:
            return 42

        stats = test_func()
        assert stats.name == name
        assert stats.count == 3


class TestRegressionResult:
    """Property tests for RegressionResult."""

    @given(severity=st.sampled_from(list(RegressionSeverity)))
    @settings(max_examples=100)
    def test_is_regression(self, severity: RegressionSeverity) -> None:
        """is_regression is True for non-NONE severity."""
        baseline = PerformanceBaseline(
            name="test",
            mean_ms=100.0,
            std_dev_ms=10.0,
            p95_ms=110.0,
            p99_ms=120.0,
            sample_count=10,
        )
        stats = BenchmarkStats(name="test", samples=[100.0] * 10)
        result = RegressionResult(
            benchmark_name="test",
            baseline=baseline,
            current_stats=stats,
            severity=severity,
            percent_change=0.0,
            message="test",
        )
        assert result.is_regression == (severity != RegressionSeverity.NONE)
