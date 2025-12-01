"""Cache metrics for OpenTelemetry export.

**Feature: api-base-score-100, Task 4.1: Add CacheMetrics dataclass**
**Feature: api-base-score-100, Task 4.3: Create OpenTelemetry metrics exporter**
**Validates: Requirements 3.1, 3.2, 3.3, 3.4, 3.5**
"""

import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class CacheMetrics:
    """Cache metrics for monitoring and OpenTelemetry export.

    **Feature: api-base-score-100, Task 4.1: Add CacheMetrics dataclass**
    **Validates: Requirements 3.1, 3.2, 3.3, 3.5**

    Tracks cache hits, misses, and evictions for observability.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        evictions: Number of cache evictions (LRU).

    Example:
        >>> metrics = CacheMetrics()
        >>> metrics.record_hit()
        >>> metrics.record_miss()
        >>> print(f"Hit rate: {metrics.hit_rate:.2%}")
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        **Feature: api-base-score-100, Property 9: Cache Hit Rate Calculation**
        **Validates: Requirements 3.3**

        Returns:
            Float between 0.0 and 1.0 representing hits / (hits + misses).
            Returns 0.0 if no requests have been made.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    @property
    def total_requests(self) -> int:
        """Get total number of cache requests."""
        return self.hits + self.misses

    def record_hit(self) -> None:
        """Record a cache hit.

        **Feature: api-base-score-100, Property 7: Cache Hit Counter Increment**
        **Validates: Requirements 3.1**
        """
        self.hits += 1

    def record_miss(self) -> None:
        """Record a cache miss.

        **Feature: api-base-score-100, Property 8: Cache Miss Counter Increment**
        **Validates: Requirements 3.2**
        """
        self.misses += 1

    def record_eviction(self) -> None:
        """Record a cache eviction.

        **Feature: api-base-score-100, Property 10: Cache Eviction Counter**
        **Validates: Requirements 3.5**
        """
        self.evictions += 1

    def reset(self) -> None:
        """Reset all metrics to zero."""
        self.hits = 0
        self.misses = 0
        self.evictions = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary for export."""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "evictions": self.evictions,
            "hit_rate": self.hit_rate,
            "total_requests": self.total_requests,
        }


class CacheMetricsExporter:
    """Export cache metrics to OpenTelemetry.

    **Feature: api-base-score-100, Task 4.3: Create OpenTelemetry metrics exporter**
    **Validates: Requirements 3.4**

    Creates and exports cache metrics as OpenTelemetry counters and gauges.

    Metrics exported:
        - cache.hits (Counter): Number of cache hits
        - cache.misses (Counter): Number of cache misses
        - cache.evictions (Counter): Number of cache evictions
        - cache.hit_rate (Gauge): Current cache hit rate

    Example:
        >>> exporter = CacheMetricsExporter(cache_name="user_cache")
        >>> exporter.export_metrics(metrics)
    """

    def __init__(
        self,
        cache_name: str = "default",
        meter_name: str = "my_app.cache",
    ) -> None:
        """Initialize cache metrics exporter.

        Args:
            cache_name: Name of the cache for metric labels.
            meter_name: OpenTelemetry meter name.
        """
        self._cache_name = cache_name
        self._meter_name = meter_name
        self._meter: Any = None
        self._hits_counter: Any = None
        self._misses_counter: Any = None
        self._evictions_counter: Any = None
        self._hit_rate_gauge: Any = None
        self._last_hits = 0
        self._last_misses = 0
        self._last_evictions = 0

        self._initialize_metrics()

    def _initialize_metrics(self) -> None:
        """Initialize OpenTelemetry metrics instruments."""
        try:
            from opentelemetry import metrics

            self._meter = metrics.get_meter(self._meter_name)

            self._hits_counter = self._meter.create_counter(
                name="cache.hits",
                description="Number of cache hits",
                unit="1",
            )

            self._misses_counter = self._meter.create_counter(
                name="cache.misses",
                description="Number of cache misses",
                unit="1",
            )

            self._evictions_counter = self._meter.create_counter(
                name="cache.evictions",
                description="Number of cache evictions",
                unit="1",
            )

            self._hit_rate_gauge = self._meter.create_observable_gauge(
                name="cache.hit_rate",
                description="Cache hit rate",
                unit="1",
                callbacks=[],
            )

            logger.info(
                "OpenTelemetry cache metrics initialized",
                extra={"cache_name": self._cache_name},
            )
        except ImportError:
            logger.warning(
                "OpenTelemetry not available, cache metrics will not be exported"
            )
        except Exception as e:
            logger.warning(f"Failed to initialize OpenTelemetry metrics: {e}")

    def export_metrics(self, metrics: CacheMetrics) -> None:
        """Export cache metrics to OpenTelemetry.

        **Feature: api-base-score-100, Task 4.3: Create OpenTelemetry metrics exporter**
        **Validates: Requirements 3.4**

        Args:
            metrics: CacheMetrics instance to export.
        """
        attributes = {"cache_name": self._cache_name}

        if self._hits_counter:
            delta_hits = metrics.hits - self._last_hits
            if delta_hits > 0:
                self._hits_counter.add(delta_hits, attributes)
            self._last_hits = metrics.hits

        if self._misses_counter:
            delta_misses = metrics.misses - self._last_misses
            if delta_misses > 0:
                self._misses_counter.add(delta_misses, attributes)
            self._last_misses = metrics.misses

        if self._evictions_counter:
            delta_evictions = metrics.evictions - self._last_evictions
            if delta_evictions > 0:
                self._evictions_counter.add(delta_evictions, attributes)
            self._last_evictions = metrics.evictions

        logger.debug(
            "Cache metrics exported",
            extra={
                "cache_name": self._cache_name,
                "hits": metrics.hits,
                "misses": metrics.misses,
                "evictions": metrics.evictions,
                "hit_rate": metrics.hit_rate,
            },
        )


class MetricsAwareCacheWrapper[T]:
    """Wrapper that adds metrics tracking to any cache provider.

    **Feature: api-base-score-100, Task 4.2: Integrate metrics with InMemoryCacheProvider**
    **Validates: Requirements 3.5**

    Wraps a cache provider to automatically track hits, misses, and evictions.

    Example:
        >>> from my_app.shared.caching.providers import InMemoryCacheProvider
        >>> cache = InMemoryCacheProvider[dict]()
        >>> metrics_cache = MetricsAwareCacheWrapper(cache)
        >>> await metrics_cache.set("key", {"value": 1})
        >>> result = await metrics_cache.get("key")
        >>> print(metrics_cache.metrics.hit_rate)
    """

    def __init__(
        self,
        provider: Any,
        exporter: CacheMetricsExporter | None = None,
        export_interval: int = 60,
    ) -> None:
        """Initialize metrics-aware cache wrapper.

        Args:
            provider: Underlying cache provider.
            exporter: Optional OpenTelemetry exporter.
            export_interval: Seconds between metric exports.
        """
        self._provider = provider
        self._metrics = CacheMetrics()
        self._exporter = exporter
        self._export_interval = export_interval
        self._request_count = 0

    @property
    def metrics(self) -> CacheMetrics:
        """Get current cache metrics."""
        return self._metrics

    def get_metrics(self) -> CacheMetrics:
        """Get current cache metrics (method form).

        **Feature: api-base-score-100, Task 4.2: Integrate metrics with InMemoryCacheProvider**
        **Validates: Requirements 3.5**

        Returns:
            Current CacheMetrics instance.
        """
        return self._metrics

    async def get(self, key: str) -> T | None:
        """Get value from cache with metrics tracking.

        **Feature: api-base-score-100, Property 7: Cache Hit Counter Increment**
        **Feature: api-base-score-100, Property 8: Cache Miss Counter Increment**
        **Validates: Requirements 3.1, 3.2**
        """
        result = await self._provider.get(key)

        if result is not None:
            self._metrics.record_hit()
        else:
            self._metrics.record_miss()

        self._maybe_export()
        return result

    async def set(self, key: str, value: T, ttl: int | None = None) -> None:
        """Set value in cache with eviction tracking.

        **Feature: api-base-score-100, Property 10: Cache Eviction Counter**
        **Validates: Requirements 3.5**
        """
        size_before = await self._provider.size() if hasattr(self._provider, "size") else 0
        await self._provider.set(key, value, ttl)
        size_after = await self._provider.size() if hasattr(self._provider, "size") else 0

        if hasattr(self._provider, "_config"):
            max_size = self._provider._config.max_size
            if size_before >= max_size and size_after == max_size:
                self._metrics.record_eviction()

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        return await self._provider.delete(key)

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return await self._provider.exists(key)

    async def clear(self) -> None:
        """Clear all values from cache."""
        if hasattr(self._provider, "clear"):
            await self._provider.clear()

    async def size(self) -> int:
        """Get current cache size."""
        if hasattr(self._provider, "size"):
            return await self._provider.size()
        return 0

    def _maybe_export(self) -> None:
        """Export metrics if exporter is configured."""
        self._request_count += 1
        if self._exporter and self._request_count % self._export_interval == 0:
            self._exporter.export_metrics(self._metrics)
