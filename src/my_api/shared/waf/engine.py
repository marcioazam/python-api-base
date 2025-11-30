"""WAF rule engine for threat inspection.

**Feature: file-size-compliance-phase2, Task 2.1**
**Validates: Requirements 1.1, 5.1, 5.2, 5.3**
"""

from collections.abc import Callable

from .models import ThreatDetection, WAFRequest, WAFRule


class WAFRuleEngine:
    """Rule engine for WAF."""

    def __init__(self) -> None:
        """Initialize rule engine."""
        self._rules: dict[str, WAFRule] = {}
        self._custom_validators: list[Callable[[WAFRequest], ThreatDetection | None]] = []

    def add_rule(self, rule: WAFRule) -> "WAFRuleEngine":
        """Add a rule to the engine."""
        self._rules[rule.id] = rule
        return self

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a rule by ID."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            return True
        return False

    def get_rule(self, rule_id: str) -> WAFRule | None:
        """Get a rule by ID."""
        return self._rules.get(rule_id)

    def enable_rule(self, rule_id: str) -> bool:
        """Enable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = True
            return True
        return False

    def disable_rule(self, rule_id: str) -> bool:
        """Disable a rule."""
        rule = self._rules.get(rule_id)
        if rule:
            rule.enabled = False
            return True
        return False

    def add_custom_validator(
        self,
        validator: Callable[[WAFRequest], ThreatDetection | None],
    ) -> "WAFRuleEngine":
        """Add custom validation function."""
        self._custom_validators.append(validator)
        return self

    def _check_value(
        self,
        value: str,
        target: str,
    ) -> list[ThreatDetection]:
        """Check a value against all rules."""
        detections: list[ThreatDetection] = []
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if target not in rule.targets:
                continue
            if rule.matches(value):
                detections.append(
                    ThreatDetection(
                        detected=True,
                        rule=rule,
                        matched_value=value[:100],
                        target=target,
                    )
                )
        return detections

    def inspect(self, request: WAFRequest) -> list[ThreatDetection]:
        """Inspect request against all rules."""
        all_detections: list[ThreatDetection] = []

        for key, value in request.query_params.items():
            all_detections.extend(self._check_value(f"{key}={value}", "query"))

        for key, value in request.headers.items():
            all_detections.extend(self._check_value(f"{key}: {value}", "headers"))

        if request.body:
            all_detections.extend(self._check_value(request.body, "body"))

        all_detections.extend(self._check_value(request.path, "path"))

        for validator in self._custom_validators:
            result = validator(request)
            if result and result.detected:
                all_detections.append(result)

        return all_detections

    def list_rules(self) -> list[WAFRule]:
        """List all rules."""
        return list(self._rules.values())

    def get_enabled_rules(self) -> list[WAFRule]:
        """Get only enabled rules."""
        return [r for r in self._rules.values() if r.enabled]
