"""Prometheus metrics decorators.

**Feature: observability-infrastructure**
**Requirement: R5 - Prometheus Metrics**
"""

from __future__ import annotations

import asyncio
import functools
import time
from collections.abc import Callable
from typing import ParamSpec, TypeVar

from infrastructure.prometheus.registry import get_registry

P = ParamSpec("P")
R = TypeVar("R")


def counter(
    name: str,
    description: str,
    labels: list[str] | None = None,
    label_values: dict[str, str] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to count function calls.

    **Feature: observability-infrastructure**
    **Requirement: R5.2 - Metrics Decorators**

    Example:
        >>> @counter("api_calls_total", "Total API calls", ["endpoint"])
        ... def handle_request():
        ...     pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        metric = get_registry().counter(name, description, labels)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if label_values:
                metric.labels(**label_values).inc()
            else:
                metric.inc()
            return func(*args, **kwargs)

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            if label_values:
                metric.labels(**label_values).inc()
            else:
                metric.inc()
            return await func(*args, **kwargs)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


def gauge(
    name: str,
    description: str,
    labels: list[str] | None = None,
    label_values: dict[str, str] | None = None,
    track_inprogress: bool = True,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to track in-progress calls with a gauge.

    Example:
        >>> @gauge("active_requests", "Active requests", track_inprogress=True)
        ... async def handle_request():
        ...     pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        metric = get_registry().gauge(name, description, labels)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            g = metric.labels(**label_values) if label_values else metric
            if track_inprogress:
                g.inc()
            try:
                return func(*args, **kwargs)
            finally:
                if track_inprogress:
                    g.dec()

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            g = metric.labels(**label_values) if label_values else metric
            if track_inprogress:
                g.inc()
            try:
                return await func(*args, **kwargs)
            finally:
                if track_inprogress:
                    g.dec()

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


def histogram(
    name: str,
    description: str,
    labels: list[str] | None = None,
    label_values: dict[str, str] | None = None,
    buckets: tuple[float, ...] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to track function duration in a histogram.

    Example:
        >>> @histogram("request_duration_seconds", "Request duration")
        ... async def handle_request():
        ...     pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        metric = get_registry().histogram(name, description, labels, buckets)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                if label_values:
                    metric.labels(**label_values).observe(duration)
                else:
                    metric.observe(duration)

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                if label_values:
                    metric.labels(**label_values).observe(duration)
                else:
                    metric.observe(duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


def summary(
    name: str,
    description: str,
    labels: list[str] | None = None,
    label_values: dict[str, str] | None = None,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to track function duration in a summary.

    Example:
        >>> @summary("request_duration_seconds", "Request duration")
        ... async def handle_request():
        ...     pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        metric = get_registry().summary(name, description, labels)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                if label_values:
                    metric.labels(**label_values).observe(duration)
                else:
                    metric.observe(duration)

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            start = time.perf_counter()
            try:
                return await func(*args, **kwargs)
            finally:
                duration = time.perf_counter() - start
                if label_values:
                    metric.labels(**label_values).observe(duration)
                else:
                    metric.observe(duration)

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator


# Alias for histogram (common naming convention)
timer = histogram


def count_exceptions(
    name: str,
    description: str,
    labels: list[str] | None = None,
    label_values: dict[str, str] | None = None,
    exception_type: type[Exception] = Exception,
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Decorator to count exceptions.

    Example:
        >>> @count_exceptions("errors_total", "Total errors", ["type"])
        ... async def handle_request():
        ...     pass
    """

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        all_labels = (labels or []) + ["exception_type"]
        metric = get_registry().counter(name, description, all_labels)

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return func(*args, **kwargs)
            except exception_type as e:
                label_vals = {
                    **(label_values or {}),
                    "exception_type": type(e).__name__,
                }
                metric.labels(**label_vals).inc()
                raise

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            try:
                return await func(*args, **kwargs)
            except exception_type as e:
                label_vals = {
                    **(label_values or {}),
                    "exception_type": type(e).__name__,
                }
                metric.labels(**label_vals).inc()
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper  # type: ignore
        return sync_wrapper

    return decorator
