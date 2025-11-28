"""Property-based tests for Web Application Firewall (WAF).

**Feature: api-architecture-analysis, Priority 11.1: WAF**
**Validates: Requirements 5.3, 5.5**
"""

from hypothesis import given, settings
from hypothesis import strategies as st

from my_api.shared.waf import (
    RuleAction,
    RuleSeverity,
    ThreatDetection,
    ThreatType,
    WAFMiddleware,
    WAFRequest,
    WAFRule,
    WAFRuleEngine,
)


class TestWAFRuleProperties:
    """Property tests for WAFRule."""

    def test_rule_matches_sql_injection(self) -> None:
        """Rule SHALL detect SQL injection patterns."""
        rule = WAFRule(
            id="test-sqli",
            name="SQL Injection Test",
            threat_type=ThreatType.SQL_INJECTION,
            pattern=r"(\bSELECT\b.*\bFROM\b)",
        )

        assert rule.matches("SELECT * FROM users") is True
        assert rule.matches("normal text") is False

    def test_rule_matches_xss(self) -> None:
        """Rule SHALL detect XSS patterns."""
        rule = WAFRule(
            id="test-xss",
            name="XSS Test",
            threat_type=ThreatType.XSS,
            pattern=r"(<script[^>]*>)",
        )

        assert rule.matches("<script>alert('xss')</script>") is True
        assert rule.matches("normal text") is False

    def test_rule_matches_path_traversal(self) -> None:
        """Rule SHALL detect path traversal patterns."""
        rule = WAFRule(
            id="test-path",
            name="Path Traversal Test",
            threat_type=ThreatType.PATH_TRAVERSAL,
            pattern=r"(\.\.\/)",
        )

        assert rule.matches("../../../etc/passwd") is True
        assert rule.matches("/normal/path") is False

    def test_disabled_rule_does_not_match(self) -> None:
        """Disabled rule SHALL not match anything."""
        rule = WAFRule(
            id="test",
            name="Test",
            threat_type=ThreatType.SQL_INJECTION,
            pattern=r"SELECT",
            enabled=False,
        )

        assert rule.matches("SELECT * FROM users") is False

    @settings(max_examples=20)
    @given(
        rule_id=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz0123456789"),
        name=st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789 "),
    )
    def test_rule_preserves_metadata(self, rule_id: str, name: str) -> None:
        """Rule SHALL preserve id and name."""
        rule = WAFRule(
            id=rule_id,
            name=name,
            threat_type=ThreatType.CUSTOM,
            pattern=r"test",
        )

        assert rule.id == rule_id
        assert rule.name == name


class TestWAFRuleEngineProperties:
    """Property tests for WAFRuleEngine."""

    def test_engine_adds_and_retrieves_rules(self) -> None:
        """Engine SHALL add and retrieve rules."""
        engine = WAFRuleEngine()
        rule = WAFRule(
            id="test-1",
            name="Test Rule",
            threat_type=ThreatType.SQL_INJECTION,
            pattern=r"SELECT",
        )

        engine.add_rule(rule)

        assert engine.get_rule("test-1") is rule
        assert "test-1" in [r.id for r in engine.list_rules()]

    def test_engine_removes_rules(self) -> None:
        """Engine SHALL remove rules."""
        engine = WAFRuleEngine()
        rule = WAFRule(
            id="test-1",
            name="Test Rule",
            threat_type=ThreatType.SQL_INJECTION,
            pattern=r"SELECT",
        )

        engine.add_rule(rule)
        assert engine.remove_rule("test-1") is True
        assert engine.get_rule("test-1") is None

    def test_engine_enables_disables_rules(self) -> None:
        """Engine SHALL enable and disable rules."""
        engine = WAFRuleEngine()
        rule = WAFRule(
            id="test-1",
            name="Test Rule",
            threat_type=ThreatType.SQL_INJECTION,
            pattern=r"SELECT",
            enabled=True,
        )

        engine.add_rule(rule)

        assert engine.disable_rule("test-1") is True
        assert engine.get_rule("test-1").enabled is False

        assert engine.enable_rule("test-1") is True
        assert engine.get_rule("test-1").enabled is True

    def test_engine_inspects_query_params(self) -> None:
        """Engine SHALL inspect query parameters."""
        engine = WAFRuleEngine()
        engine.add_rule(
            WAFRule(
                id="sqli",
                name="SQL Injection",
                threat_type=ThreatType.SQL_INJECTION,
                pattern=r"SELECT.*FROM",
                targets=["query"],
            )
        )

        request = WAFRequest(
            method="GET",
            path="/api/users",
            query_params={"q": "SELECT * FROM users"},
        )

        detections = engine.inspect(request)

        assert len(detections) == 1
        assert detections[0].threat_type == ThreatType.SQL_INJECTION

    def test_engine_inspects_body(self) -> None:
        """Engine SHALL inspect request body."""
        engine = WAFRuleEngine()
        engine.add_rule(
            WAFRule(
                id="xss",
                name="XSS",
                threat_type=ThreatType.XSS,
                pattern=r"<script>",
                targets=["body"],
            )
        )

        request = WAFRequest(
            method="POST",
            path="/api/comments",
            body='{"comment": "<script>alert(1)</script>"}',
        )

        detections = engine.inspect(request)

        assert len(detections) == 1
        assert detections[0].threat_type == ThreatType.XSS

    def test_engine_respects_target_filter(self) -> None:
        """Engine SHALL respect target filter."""
        engine = WAFRuleEngine()
        engine.add_rule(
            WAFRule(
                id="test",
                name="Test",
                threat_type=ThreatType.SQL_INJECTION,
                pattern=r"SELECT",
                targets=["body"],  # Only check body
            )
        )

        request = WAFRequest(
            method="GET",
            path="/api/users",
            query_params={"q": "SELECT"},  # In query, not body
        )

        detections = engine.inspect(request)

        assert len(detections) == 0


class TestWAFMiddlewareProperties:
    """Property tests for WAFMiddleware."""

    def test_middleware_blocks_sql_injection(self) -> None:
        """Middleware SHALL block SQL injection."""
        waf = WAFMiddleware(enabled=True, block_on_detection=True)

        request = WAFRequest(
            method="GET",
            path="/api/users",
            query_params={"id": "1 OR 1=1"},
        )

        response = waf.inspect_request(request)

        assert response.allowed is False
        assert response.threat_count > 0

    def test_middleware_blocks_xss(self) -> None:
        """Middleware SHALL block XSS attacks."""
        waf = WAFMiddleware(enabled=True, block_on_detection=True)

        request = WAFRequest(
            method="POST",
            path="/api/comments",
            body="<script>alert('xss')</script>",
        )

        response = waf.inspect_request(request)

        assert response.allowed is False
        assert response.threat_count > 0

    def test_middleware_blocks_path_traversal(self) -> None:
        """Middleware SHALL block path traversal."""
        waf = WAFMiddleware(enabled=True, block_on_detection=True)

        request = WAFRequest(
            method="GET",
            path="/api/files/../../../etc/passwd",
        )

        response = waf.inspect_request(request)

        assert response.allowed is False
        assert response.threat_count > 0

    def test_middleware_allows_safe_requests(self) -> None:
        """Middleware SHALL allow safe requests."""
        waf = WAFMiddleware(enabled=True, block_on_detection=True)

        request = WAFRequest(
            method="GET",
            path="/api/users",
            query_params={"page": "1", "limit": "10"},
        )

        response = waf.inspect_request(request)

        assert response.allowed is True
        assert response.threat_count == 0

    def test_middleware_respects_whitelist(self) -> None:
        """Middleware SHALL respect IP whitelist."""
        waf = WAFMiddleware(enabled=True, block_on_detection=True)
        waf.add_to_whitelist("192.168.1.100")

        request = WAFRequest(
            method="GET",
            path="/api/users",
            query_params={"id": "1 OR 1=1"},
            client_ip="192.168.1.100",
        )

        response = waf.inspect_request(request)

        assert response.allowed is True

    def test_middleware_disabled_allows_all(self) -> None:
        """Disabled middleware SHALL allow all requests."""
        waf = WAFMiddleware(enabled=False)

        request = WAFRequest(
            method="GET",
            path="/api/users",
            query_params={"id": "1 OR 1=1"},
        )

        response = waf.inspect_request(request)

        assert response.allowed is True

    def test_middleware_logs_detections(self) -> None:
        """Middleware SHALL log detections."""
        waf = WAFMiddleware(enabled=True, log_detections=True)

        request = WAFRequest(
            method="GET",
            path="/api/users",
            query_params={"id": "1 OR 1=1"},
        )

        waf.inspect_request(request)
        log = waf.get_detection_log()

        assert len(log) > 0

    def test_middleware_clears_log(self) -> None:
        """Middleware SHALL clear detection log."""
        waf = WAFMiddleware(enabled=True, log_detections=True)

        request = WAFRequest(
            method="GET",
            path="/api/users",
            query_params={"id": "1 OR 1=1"},
        )

        waf.inspect_request(request)
        waf.clear_detection_log()

        assert len(waf.get_detection_log()) == 0

    def test_middleware_provides_stats(self) -> None:
        """Middleware SHALL provide statistics."""
        waf = WAFMiddleware(enabled=True)
        stats = waf.get_stats()

        assert "enabled" in stats
        assert "total_rules" in stats
        assert "enabled_rules" in stats
        assert stats["total_rules"] > 0

    def test_middleware_adds_custom_rules(self) -> None:
        """Middleware SHALL accept custom rules."""
        waf = WAFMiddleware(enabled=True)

        custom_rule = WAFRule(
            id="custom-1",
            name="Custom Rule",
            threat_type=ThreatType.CUSTOM,
            pattern=r"forbidden_word",
        )

        waf.add_custom_rule(custom_rule)

        request = WAFRequest(
            method="POST",
            path="/api/data",
            body="This contains forbidden_word",
        )

        response = waf.inspect_request(request)

        assert response.threat_count > 0


class TestThreatDetectionProperties:
    """Property tests for ThreatDetection."""

    def test_detection_has_threat_type(self) -> None:
        """Detection SHALL expose threat type from rule."""
        rule = WAFRule(
            id="test",
            name="Test",
            threat_type=ThreatType.SQL_INJECTION,
            pattern=r"test",
        )

        detection = ThreatDetection(
            detected=True,
            rule=rule,
            matched_value="test",
            target="body",
        )

        assert detection.threat_type == ThreatType.SQL_INJECTION

    def test_detection_has_severity(self) -> None:
        """Detection SHALL expose severity from rule."""
        rule = WAFRule(
            id="test",
            name="Test",
            threat_type=ThreatType.XSS,
            pattern=r"test",
            severity=RuleSeverity.CRITICAL,
        )

        detection = ThreatDetection(
            detected=True,
            rule=rule,
        )

        assert detection.severity == RuleSeverity.CRITICAL

    def test_detection_without_rule_has_none_properties(self) -> None:
        """Detection without rule SHALL have None properties."""
        detection = ThreatDetection(detected=False)

        assert detection.threat_type is None
        assert detection.severity is None


class TestWAFRequestProperties:
    """Property tests for WAFRequest."""

    @settings(max_examples=20)
    @given(
        method=st.sampled_from(["GET", "POST", "PUT", "DELETE"]),
        path=st.text(min_size=1, max_size=30, alphabet="abcdefghijklmnopqrstuvwxyz0123456789").map(lambda x: f"/{x}"),
    )
    def test_request_preserves_method_and_path(self, method: str, path: str) -> None:
        """WAFRequest SHALL preserve method and path."""
        request = WAFRequest(method=method, path=path)

        assert request.method == method
        assert request.path == path

    def test_request_has_default_empty_collections(self) -> None:
        """WAFRequest SHALL have empty default collections."""
        request = WAFRequest(method="GET", path="/")

        assert request.query_params == {}
        assert request.headers == {}
        assert request.body is None
