"""Performance Baseline and Regression Testing Module."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
from collections.abc import Callable
import json
import statistics
import time


class RegressionSeverity(Enum):
    """Severity of performance regression."""
    NONE = "none"
    MINOR = "minor"
    MODERATE = "moderate"
    SEVERE = "severe"
    CRITICAL = "critical"


@dataclass(frozen=True, slots=True)
class BenchmarkResult:
    """Result of a single benchmark run."""
    name: str
    duration_ms: float
    memory_bytes: int = 0
    iterations: int = 1
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def duration_per_iteration(self) -> float:
        if self.iterations > 0:
            return self.duration_ms / self.iterations
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "duration_ms": self.duration_ms,
            "memory_bytes": self.memory_bytes,
            "iterations": self.iterations,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class BenchmarkStats:
    """Statistical summary of benchmark results."""
    name: str
    samples: list[float] = field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.samples)

    @property
    def mean(self) -> float:
        return statistics.mean(self.samples) if self.samples else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.samples) if self.samples else 0.0

    @property
    def std_dev(self) -> float:
        return statistics.stdev(self.samples) if len(self.samples) >= 2 else 0.0

    @property
    def min_value(self) -> float:
        return min(self.samples) if self.samples else 0.0

    @property
    def max_value(self) -> float:
        return max(self.samples) if self.samples else 0.0

    @property
    def p95(self) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        return s[min(int(len(s) * 0.95), len(s) - 1)]

    @property
    def p99(self) -> float:
        if not self.samples:
            return 0.0
        s = sorted(self.samples)
        return s[min(int(len(s) * 0.99), len(s) - 1)]

    def add_sample(self, duration_ms: float) -> None:
        self.samples.append(duration_ms)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "count": self.count, "mean": self.mean,
                "median": self.median, "std_dev": self.std_dev,
                "min": self.min_value, "max": self.max_value,
                "p95": self.p95, "p99": self.p99}


@dataclass
class PerformanceBaseline:
    """Performance baseline for a benchmark."""
    name: str
    mean_ms: float
    std_dev_ms: float
    p95_ms: float
    p99_ms: float
    sample_count: int
    created_at: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"

    @classmethod
    def from_stats(cls, stats: BenchmarkStats, version: str = "1.0.0") -> "PerformanceBaseline":
        return cls(name=stats.name, mean_ms=stats.mean, std_dev_ms=stats.std_dev,
                   p95_ms=stats.p95, p99_ms=stats.p99, sample_count=stats.count, version=version)

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "mean_ms": self.mean_ms, "std_dev_ms": self.std_dev_ms,
                "p95_ms": self.p95_ms, "p99_ms": self.p99_ms, "sample_count": self.sample_count,
                "created_at": self.created_at.isoformat(), "version": self.version}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PerformanceBaseline":
        return cls(name=data["name"], mean_ms=data["mean_ms"], std_dev_ms=data["std_dev_ms"],
                   p95_ms=data["p95_ms"], p99_ms=data["p99_ms"], sample_count=data["sample_count"],
                   created_at=datetime.fromisoformat(data["created_at"]),
                   version=data.get("version", "1.0.0"))


@dataclass
class RegressionResult:
    """Result of regression analysis."""
    benchmark_name: str
    baseline: PerformanceBaseline
    current_stats: BenchmarkStats
    severity: RegressionSeverity
    percent_change: float
    message: str

    @property
    def is_regression(self) -> bool:
        return self.severity != RegressionSeverity.NONE

    def to_dict(self) -> dict[str, Any]:
        return {"benchmark_name": self.benchmark_name, "severity": self.severity.value,
                "percent_change": self.percent_change, "message": self.message,
                "baseline_mean_ms": self.baseline.mean_ms, "current_mean_ms": self.current_stats.mean}


@dataclass
class RegressionConfig:
    """Configuration for regression detection."""
    minor_threshold_percent: float = 10.0
    moderate_threshold_percent: float = 25.0
    severe_threshold_percent: float = 50.0
    critical_threshold_percent: float = 100.0
    use_std_dev: bool = True
    std_dev_multiplier: float = 2.0

    def get_severity(self, percent_change: float) -> RegressionSeverity:
        if percent_change < self.minor_threshold_percent:
            return RegressionSeverity.NONE
        if percent_change < self.moderate_threshold_percent:
            return RegressionSeverity.MINOR
        if percent_change < self.severe_threshold_percent:
            return RegressionSeverity.MODERATE
        if percent_change < self.critical_threshold_percent:
            return RegressionSeverity.SEVERE
        return RegressionSeverity.CRITICAL


class BaselineStore:
    """Stores and retrieves performance baselines."""
    def __init__(self, storage_path: Path) -> None:
        self._storage_path = storage_path
        self._baselines: dict[str, PerformanceBaseline] = {}
        self._load()

    def _load(self) -> None:
        if not self._storage_path.exists():
            return
        try:
            with open(self._storage_path) as f:
                data = json.load(f)
            for name, bd in data.items():
                self._baselines[name] = PerformanceBaseline.from_dict(bd)
        except (json.JSONDecodeError, OSError, KeyError):
            pass

    def _save(self) -> None:
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        data = {n: b.to_dict() for n, b in self._baselines.items()}
        with open(self._storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def get(self, name: str) -> PerformanceBaseline | None:
        return self._baselines.get(name)

    def set(self, baseline: PerformanceBaseline) -> None:
        self._baselines[baseline.name] = baseline
        self._save()

    def delete(self, name: str) -> bool:
        if name in self._baselines:
            del self._baselines[name]
            self._save()
            return True
        return False

    def list_all(self) -> list[str]:
        return list(self._baselines.keys())

    def clear(self) -> None:
        self._baselines.clear()
        self._save()


class RegressionDetector:
    """Detects performance regressions."""
    def __init__(self, store: BaselineStore, config: RegressionConfig | None = None) -> None:
        self._store = store
        self._config = config or RegressionConfig()

    def analyze(self, stats: BenchmarkStats) -> RegressionResult:
        baseline = self._store.get(stats.name)
        if baseline is None:
            return RegressionResult(benchmark_name=stats.name,
                baseline=PerformanceBaseline.from_stats(stats), current_stats=stats,
                severity=RegressionSeverity.NONE, percent_change=0.0, message="No baseline found")
        pct = self._calc_change(baseline, stats)
        sev = self._config.get_severity(pct)
        msg = self._gen_msg(baseline, stats, pct, sev)
        return RegressionResult(benchmark_name=stats.name, baseline=baseline,
            current_stats=stats, severity=sev, percent_change=pct, message=msg)

    def _calc_change(self, baseline: PerformanceBaseline, stats: BenchmarkStats) -> float:
        if baseline.mean_ms == 0:
            return 0.0
        return max(0.0, ((stats.mean - baseline.mean_ms) / baseline.mean_ms) * 100)

    def _gen_msg(self, bl: PerformanceBaseline, st: BenchmarkStats, pct: float, sev: RegressionSeverity) -> str:
        if sev == RegressionSeverity.NONE:
            return f"Performance within acceptable range ({pct:.1f}% change)"
        return f"{sev.value.upper()} regression: {pct:.1f}% slower (baseline: {bl.mean_ms:.2f}ms, current: {st.mean:.2f}ms)"


class Benchmark:
    """Benchmark runner."""
    def __init__(self, name: str, warmup_iterations: int = 3, measure_iterations: int = 10) -> None:
        self._name = name
        self._warmup = warmup_iterations
        self._iterations = measure_iterations
        self._stats = BenchmarkStats(name=name)

    @property
    def name(self) -> str:
        return self._name

    @property
    def stats(self) -> BenchmarkStats:
        return self._stats

    def run[T](self, func: Callable[[], T]) -> BenchmarkStats:
        for _ in range(self._warmup):
            func()
        self._stats = BenchmarkStats(name=self._name)
        for _ in range(self._iterations):
            start = time.perf_counter()
            func()
            end = time.perf_counter()
            self._stats.add_sample((end - start) * 1000)
        return self._stats


class BenchmarkSuite:
    """Suite of benchmarks."""
    def __init__(self, name: str) -> None:
        self._name = name
        self._benchmarks: dict[str, Callable[[], Any]] = {}
        self._results: dict[str, BenchmarkStats] = {}

    @property
    def name(self) -> str:
        return self._name

    def add(self, name: str, func: Callable[[], Any]) -> None:
        self._benchmarks[name] = func

    def run_all(self, warmup: int = 3, iterations: int = 10) -> dict[str, BenchmarkStats]:
        self._results = {}
        for name, func in self._benchmarks.items():
            self._results[name] = Benchmark(name, warmup, iterations).run(func)
        return self._results

    def get_results(self) -> dict[str, BenchmarkStats]:
        return self._results


@dataclass
class ComparisonReport:
    """Report comparing two benchmark runs."""
    timestamp: datetime = field(default_factory=datetime.now)
    regressions: list[RegressionResult] = field(default_factory=list)
    improvements: list[RegressionResult] = field(default_factory=list)
    unchanged: list[str] = field(default_factory=list)

    @property
    def has_regressions(self) -> bool:
        return len(self.regressions) > 0

    @property
    def worst_regression(self) -> RegressionResult | None:
        return max(self.regressions, key=lambda r: r.percent_change) if self.regressions else None

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp.isoformat(),
                "regressions": [r.to_dict() for r in self.regressions],
                "improvements": [r.to_dict() for r in self.improvements],
                "unchanged": self.unchanged, "has_regressions": self.has_regressions}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def generate_summary(self) -> str:
        lines = ["Performance Comparison Report", "=" * 40, f"Timestamp: {self.timestamp.isoformat()}", ""]
        if self.regressions:
            lines.append(f"Regressions: {len(self.regressions)}")
            for r in self.regressions:
                lines.append(f"  - {r.benchmark_name}: {r.message}")
        else:
            lines.append("No regressions detected")
        if self.improvements:
            lines.append(f"\nImprovements: {len(self.improvements)}")
            for r in self.improvements:
                lines.append(f"  - {r.benchmark_name}: {abs(r.percent_change):.1f}% faster")
        lines.append(f"\nUnchanged: {len(self.unchanged)}")
        return "\n".join(lines)


class PerformanceTracker:
    """Tracks performance over time."""
    def __init__(self, storage_path: Path, config: RegressionConfig | None = None) -> None:
        self._store = BaselineStore(storage_path)
        self._config = config or RegressionConfig()
        self._detector = RegressionDetector(self._store, self._config)

    def update_baseline(self, stats: BenchmarkStats, version: str = "1.0.0") -> None:
        self._store.set(PerformanceBaseline.from_stats(stats, version))

    def check_regression(self, stats: BenchmarkStats) -> RegressionResult:
        return self._detector.analyze(stats)

    def compare_suite(self, results: dict[str, BenchmarkStats]) -> ComparisonReport:
        report = ComparisonReport()
        for name, stats in results.items():
            result = self._detector.analyze(stats)
            if result.is_regression:
                report.regressions.append(result)
            elif result.percent_change < -self._config.minor_threshold_percent:
                report.improvements.append(result)
            else:
                report.unchanged.append(name)
        return report

    def get_baseline(self, name: str) -> PerformanceBaseline | None:
        return self._store.get(name)

    def list_baselines(self) -> list[str]:
        return self._store.list_all()


def benchmark[T](name: str, warmup: int = 3, iterations: int = 10) -> Callable[[Callable[[], T]], Callable[[], BenchmarkStats]]:
    """Decorator to benchmark a function."""
    def decorator(func: Callable[[], T]) -> Callable[[], BenchmarkStats]:
        def wrapper() -> BenchmarkStats:
            return Benchmark(name, warmup, iterations).run(func)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator
