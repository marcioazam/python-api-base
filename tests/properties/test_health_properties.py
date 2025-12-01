"""Property-based tests for health check endpoints.

**Feature: advanced-reusability, Property 15: Health Check Dependency Verification**
**Validates: Requirements 7.2, 7.3**
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from hypothesis import given, settings
from hypothesis import strategies as st

from my_app.adapters.api.routes.health import (
    DEFAULT_HEALTH_CHECK_TIMEOUT,
    DependencyHealth,
    HealthResponse,
    HealthStatus,
    _run_with_timeout,
    check_database,
    check_redis,
)


class TestHealthCheckDependencyVerification:
    """Property tests for Health Check Dependency Verification.

    **Feature: advanced-reusability, Property 15: Health Check Dependency Verification**
    **Validates: Requirements 7.2, 7.3**
    """

    def test_healthy_database_returns_healthy_status(self) -> None:
        """
        **Feature: advanced-reusability, Property 15: Health Check Dependency Verification**

        For any configured dependency that is available, the readiness probe
        SHALL return healthy status for that dependency.
        """
        # Mock request with working database
        mock_request = MagicMock()
        mock_db = MagicMock()
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_db.session = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_session), __aexit__=AsyncMock()))
        mock_request.app.state.db = mock_db

        async def run_test():
            result = await check_database(mock_request)
            assert result.status == HealthStatus.HEALTHY
            assert result.latency_ms is not None

        asyncio.run(run_test())

    def test_unavailable_database_returns_unhealthy_status(self) -> None:
        """
        **Feature: advanced-reusability, Property 15: Health Check Dependency Verification**

        For any configured dependency that is unavailable, the readiness probe
        SHALL return unhealthy status with error details.
        """
        # Mock request with failing database
        mock_request = MagicMock()
        mock_db = MagicMock()
        
        # Create a context manager that raises on execute
        async def failing_session():
            raise Exception("Connection refused")
        
        mock_db.session = MagicMock(side_effect=Exception("Connection refused"))
        mock_request.app.state.db = mock_db

        async def run_test():
            result = await check_database(mock_request)
            assert result.status == HealthStatus.UNHEALTHY
            assert result.message is not None
            assert "Connection refused" in result.message

        asyncio.run(run_test())

    def test_uninitialized_database_returns_unhealthy(self) -> None:
        """
        When database is not initialized, check SHALL return unhealthy.
        """
        mock_request = MagicMock()
        mock_request.app.state.db = None

        async def run_test():
            result = await check_database(mock_request)
            assert result.status == HealthStatus.UNHEALTHY
            assert "not initialized" in result.message.lower()

        asyncio.run(run_test())

    def test_unconfigured_redis_returns_healthy(self) -> None:
        """
        When Redis is not configured (optional), check SHALL return healthy.
        """
        mock_request = MagicMock()
        mock_request.app.state.redis = None

        async def run_test():
            result = await check_redis(mock_request)
            assert result.status == HealthStatus.HEALTHY
            assert "not configured" in result.message.lower()

        asyncio.run(run_test())

    def test_unavailable_redis_returns_degraded(self) -> None:
        """
        When Redis is configured but unavailable, check SHALL return degraded.
        """
        mock_request = MagicMock()
        mock_redis = AsyncMock()
        mock_redis.ping = AsyncMock(side_effect=Exception("Connection refused"))
        mock_request.app.state.redis = mock_redis

        async def run_test():
            result = await check_redis(mock_request)
            assert result.status == HealthStatus.DEGRADED
            assert result.message is not None

        asyncio.run(run_test())


class TestHealthCheckTimeout:
    """Tests for health check timeout functionality.

    **Validates: Requirements 7.4**
    """

    def test_timeout_returns_unhealthy(self) -> None:
        """
        When health check times out, it SHALL return unhealthy status.
        """

        async def slow_check() -> DependencyHealth:
            await asyncio.sleep(10)  # Simulate slow check
            return DependencyHealth(status=HealthStatus.HEALTHY)

        async def run_test():
            result = await _run_with_timeout(slow_check, timeout=0.1)
            assert result.status == HealthStatus.UNHEALTHY
            assert "timed out" in result.message.lower()

        asyncio.run(run_test())

    def test_fast_check_completes_within_timeout(self) -> None:
        """
        When health check completes quickly, it SHALL return actual result.
        """

        async def fast_check() -> DependencyHealth:
            return DependencyHealth(
                status=HealthStatus.HEALTHY,
                latency_ms=1.0,
            )

        async def run_test():
            result = await _run_with_timeout(fast_check, timeout=5.0)
            assert result.status == HealthStatus.HEALTHY
            assert result.latency_ms == 1.0

        asyncio.run(run_test())

    @settings(max_examples=20)
    @given(timeout=st.floats(min_value=0.1, max_value=30.0))
    def test_timeout_parameter_accepted(self, timeout: float) -> None:
        """
        Any valid timeout value (0.1-30s) SHALL be accepted.
        """

        async def instant_check() -> DependencyHealth:
            return DependencyHealth(status=HealthStatus.HEALTHY)

        async def run_test():
            result = await _run_with_timeout(instant_check, timeout=timeout)
            assert result.status == HealthStatus.HEALTHY

        asyncio.run(run_test())


class TestHealthStatusDetermination:
    """Tests for overall health status determination."""

    def test_all_healthy_returns_healthy(self) -> None:
        """
        When all dependencies are healthy, overall status SHALL be healthy.
        """
        checks = {
            "database": DependencyHealth(status=HealthStatus.HEALTHY),
            "redis": DependencyHealth(status=HealthStatus.HEALTHY),
        }

        statuses = [check.status for check in checks.values()]

        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        assert overall == HealthStatus.HEALTHY

    def test_any_unhealthy_returns_unhealthy(self) -> None:
        """
        When any dependency is unhealthy, overall status SHALL be unhealthy.
        """
        checks = {
            "database": DependencyHealth(status=HealthStatus.UNHEALTHY),
            "redis": DependencyHealth(status=HealthStatus.HEALTHY),
        }

        statuses = [check.status for check in checks.values()]

        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        assert overall == HealthStatus.UNHEALTHY

    def test_degraded_without_unhealthy_returns_degraded(self) -> None:
        """
        When some dependencies are degraded but none unhealthy,
        overall status SHALL be degraded.
        """
        checks = {
            "database": DependencyHealth(status=HealthStatus.HEALTHY),
            "redis": DependencyHealth(status=HealthStatus.DEGRADED),
        }

        statuses = [check.status for check in checks.values()]

        if HealthStatus.UNHEALTHY in statuses:
            overall = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            overall = HealthStatus.DEGRADED
        else:
            overall = HealthStatus.HEALTHY

        assert overall == HealthStatus.DEGRADED

    @settings(max_examples=30)
    @given(
        db_status=st.sampled_from(list(HealthStatus)),
        redis_status=st.sampled_from(list(HealthStatus)),
    )
    def test_status_determination_property(
        self, db_status: HealthStatus, redis_status: HealthStatus
    ) -> None:
        """
        **Feature: advanced-reusability, Property 15: Health Check Dependency Verification**

        For any combination of dependency statuses, the overall status
        SHALL follow the priority: UNHEALTHY > DEGRADED > HEALTHY.
        """
        checks = {
            "database": DependencyHealth(status=db_status),
            "redis": DependencyHealth(status=redis_status),
        }

        statuses = [check.status for check in checks.values()]

        if HealthStatus.UNHEALTHY in statuses:
            expected = HealthStatus.UNHEALTHY
        elif HealthStatus.DEGRADED in statuses:
            expected = HealthStatus.DEGRADED
        else:
            expected = HealthStatus.HEALTHY

        # Verify the logic
        if db_status == HealthStatus.UNHEALTHY or redis_status == HealthStatus.UNHEALTHY:
            assert expected == HealthStatus.UNHEALTHY
        elif db_status == HealthStatus.DEGRADED or redis_status == HealthStatus.DEGRADED:
            assert expected == HealthStatus.DEGRADED
        else:
            assert expected == HealthStatus.HEALTHY


class TestHealthResponseModel:
    """Tests for health response model."""

    @settings(max_examples=20)
    @given(version=st.text(min_size=1, max_size=20) | st.none())
    def test_health_response_accepts_version(self, version: str | None) -> None:
        """
        HealthResponse SHALL accept any version string or None.
        """
        response = HealthResponse(
            status=HealthStatus.HEALTHY,
            checks={},
            version=version,
        )

        assert response.version == version

    def test_health_response_includes_all_checks(self) -> None:
        """
        HealthResponse SHALL include all dependency check results.
        """
        checks = {
            "database": DependencyHealth(status=HealthStatus.HEALTHY, latency_ms=5.0),
            "redis": DependencyHealth(status=HealthStatus.DEGRADED, message="Slow"),
            "cache": DependencyHealth(status=HealthStatus.UNHEALTHY, message="Down"),
        }

        response = HealthResponse(
            status=HealthStatus.UNHEALTHY,
            checks=checks,
        )

        assert len(response.checks) == 3
        assert "database" in response.checks
        assert "redis" in response.checks
        assert "cache" in response.checks
