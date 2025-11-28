"""Property-based tests for Coverage Enforcement module.

**Feature: api-architecture-analysis, Property 15.6: Coverage Enforcement**
**Validates: Requirements 8.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume

from src.my_api.shared.coverage_enforcement import (
    CoverageType,
    EnforcementResult,
    CoverageMetrics,
    CoverageThreshold,
    ModuleThreshold,
    EnforcementConfig,
    EnforcementViolation,
    EnforcementReport,
    CoverageEnforcer,
    parse_coverage_json,
    create_default_config,
)


# Strategies
module_names = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="_./"),
    min_size=1, max_size=50,
)
coverage_values = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)
positive_ints = st.integers(min_value=0, max_value=1000)
thresholds = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)


class TestCoverageMetrics:
    """Property tests for CoverageMetrics."""

    @given(covered=positive_ints, total=st.integers(min_value=1, max_value=1000))
    @settings(max_examples=100)
    def test_line_coverage_bounds(self, covered: int, total: int) -> None:
        """Line coverage is between 0 and 100."""
        assume(covered <= total)
        metrics = CoverageMetrics(module="test", lines_covered=covered, lines_total=total)
        assert 0.0 <= metrics.line_coverage <= 100.0

    @given(covered=positive_ints, total=st.integers(min_value=1, max_value=1000))
    @settings(max_examples=100)
    def test_branch_coverage_bounds(self, covered: int, total: int) -> None:
        """Branch coverage is between 0 and 100."""
        assume(covered <= total)
        metrics = CoverageMetrics(module="test", branches_covered=covered, branches_total=total)
        assert 0.0 <= metrics.branch_coverage <= 100.0

    @given(covered=positive_ints, total=st.integers(min_value=1, max_value=1000))
    @settings(max_examples=100)
    def test_function_coverage_bounds(self, covered: int, total: int) -> None:
        """Function coverage is between 0 and 100."""
        assume(covered <= total)
        metrics = CoverageMetrics(module="test", functions_covered=covered, functions_total=total)
        assert 0.0 <= metrics.function_coverage <= 100.0

    def test_zero_total_returns_zero(self) -> None:
        """Zero total returns 0% coverage."""
        metrics = CoverageMetrics(module="test", lines_total=0)
        assert metrics.line_coverage == 0.0

    @given(module=module_names)
    @settings(max_examples=100)
    def test_to_dict_contains_module(self, module: str) -> None:
        """to_dict contains module name."""
        metrics = CoverageMetrics(module=module)
        d = metrics.to_dict()
        assert d["module"] == module


class TestCoverageThreshold:
    """Property tests for CoverageThreshold."""

    @given(threshold=thresholds, coverage=coverage_values)
    @settings(max_examples=100)
    def test_check_line(self, threshold: float, coverage: float) -> None:
        """Line check returns correct result."""
        t = CoverageThreshold(line_threshold=threshold)
        result = t.check_line(coverage)
        assert result == (coverage >= threshold)

    @given(threshold=thresholds, coverage=coverage_values)
    @settings(max_examples=100)
    def test_check_branch(self, threshold: float, coverage: float) -> None:
        """Branch check returns correct result."""
        t = CoverageThreshold(branch_threshold=threshold)
        result = t.check_branch(coverage)
        assert result == (coverage >= threshold)

    @given(line_t=thresholds, branch_t=thresholds, func_t=thresholds)
    @settings(max_examples=100)
    def test_check_all_passes_when_all_pass(
        self, line_t: float, branch_t: float, func_t: float
    ) -> None:
        """check_all passes when all thresholds met."""
        t = CoverageThreshold(line_threshold=line_t, branch_threshold=branch_t, function_threshold=func_t)
        metrics = CoverageMetrics(
            module="test",
            lines_covered=100, lines_total=100,
            branches_covered=100, branches_total=100,
            functions_covered=100, functions_total=100)
        assert t.check_all(metrics)


class TestModuleThreshold:
    """Property tests for ModuleThreshold."""

    @given(pattern=module_names)
    @settings(max_examples=100)
    def test_exact_match(self, pattern: str) -> None:
        """Exact pattern matches exact module."""
        mt = ModuleThreshold(pattern=pattern, threshold=CoverageThreshold())
        assert mt.matches(pattern)

    @given(prefix=st.text(min_size=1, max_size=20, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=100)
    def test_wildcard_match(self, prefix: str) -> None:
        """Wildcard pattern matches prefix."""
        mt = ModuleThreshold(pattern=f"{prefix}*", threshold=CoverageThreshold())
        assert mt.matches(f"{prefix}/module.py")
        assert mt.matches(f"{prefix}something")


class TestEnforcementConfig:
    """Property tests for EnforcementConfig."""

    @given(module=module_names)
    @settings(max_examples=100)
    def test_default_threshold(self, module: str) -> None:
        """Default threshold returned for unmatched modules."""
        config = EnforcementConfig()
        threshold = config.get_threshold(module)
        assert threshold == config.default_threshold

    @given(pattern=module_names, line=thresholds, branch=thresholds)
    @settings(max_examples=100)
    def test_add_module_threshold(self, pattern: str, line: float, branch: float) -> None:
        """Added module threshold is used."""
        config = EnforcementConfig()
        config.add_module_threshold(pattern, line, branch)
        threshold = config.get_threshold(pattern)
        assert threshold.line_threshold == line
        assert threshold.branch_threshold == branch

    @given(pattern=module_names)
    @settings(max_examples=100)
    def test_exclude_pattern(self, pattern: str) -> None:
        """Excluded patterns are detected."""
        config = EnforcementConfig(exclude_patterns=[pattern])
        assert config.is_excluded(pattern)

    @given(prefix=st.text(min_size=1, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"))
    @settings(max_examples=100)
    def test_exclude_wildcard(self, prefix: str) -> None:
        """Wildcard exclusions work."""
        config = EnforcementConfig(exclude_patterns=[f"{prefix}*"])
        assert config.is_excluded(f"{prefix}/test.py")


class TestEnforcementViolation:
    """Property tests for EnforcementViolation."""

    @given(
        module=module_names,
        actual=coverage_values,
        required=coverage_values,
    )
    @settings(max_examples=100)
    def test_to_dict(self, module: str, actual: float, required: float) -> None:
        """to_dict contains all fields."""
        violation = EnforcementViolation(
            module=module, coverage_type=CoverageType.LINE,
            actual=actual, required=required, message="test")
        d = violation.to_dict()
        assert d["module"] == module
        assert d["actual"] == actual
        assert d["required"] == required


class TestEnforcementReport:
    """Property tests for EnforcementReport."""

    def test_empty_report_passed(self) -> None:
        """Empty report has passed result."""
        report = EnforcementReport()
        assert report.result == EnforcementResult.PASSED
        assert not report.has_violations

    @given(module=module_names)
    @settings(max_examples=100)
    def test_add_violation_changes_result(self, module: str) -> None:
        """Adding violation changes result to failed."""
        report = EnforcementReport()
        violation = EnforcementViolation(
            module=module, coverage_type=CoverageType.LINE,
            actual=50.0, required=80.0, message="test")
        report.add_violation(violation)
        assert report.result == EnforcementResult.FAILED
        assert report.has_violations
        assert report.violation_count == 1

    def test_to_json_valid(self) -> None:
        """to_json produces valid JSON."""
        report = EnforcementReport()
        json_str = report.to_json()
        import json
        parsed = json.loads(json_str)
        assert "result" in parsed

    def test_generate_summary(self) -> None:
        """Summary generation works."""
        report = EnforcementReport()
        summary = report.generate_summary()
        assert "Coverage Enforcement Report" in summary


class TestCoverageEnforcer:
    """Property tests for CoverageEnforcer."""

    @given(
        covered=st.integers(min_value=80, max_value=100),
        total=st.integers(min_value=100, max_value=100),
    )
    @settings(max_examples=100)
    def test_passing_coverage(self, covered: int, total: int) -> None:
        """Coverage above threshold passes."""
        config = EnforcementConfig(
            default_threshold=CoverageThreshold(line_threshold=80.0, branch_threshold=0.0, function_threshold=0.0))
        enforcer = CoverageEnforcer(config)
        metrics = CoverageMetrics(module="test", lines_covered=covered, lines_total=total)
        violations = enforcer.check_module(metrics)
        assert len(violations) == 0

    @given(
        covered=st.integers(min_value=0, max_value=79),
        total=st.integers(min_value=100, max_value=100),
    )
    @settings(max_examples=100)
    def test_failing_coverage(self, covered: int, total: int) -> None:
        """Coverage below threshold fails."""
        config = EnforcementConfig(
            default_threshold=CoverageThreshold(line_threshold=80.0, branch_threshold=0.0, function_threshold=0.0))
        enforcer = CoverageEnforcer(config)
        metrics = CoverageMetrics(module="test", lines_covered=covered, lines_total=total)
        violations = enforcer.check_module(metrics)
        assert len(violations) >= 1

    @given(module=module_names)
    @settings(max_examples=100)
    def test_excluded_module_no_violations(self, module: str) -> None:
        """Excluded modules have no violations."""
        config = EnforcementConfig(exclude_patterns=[module])
        enforcer = CoverageEnforcer(config)
        metrics = CoverageMetrics(module=module, lines_covered=0, lines_total=100)
        violations = enforcer.check_module(metrics)
        assert len(violations) == 0

    @given(
        modules=st.lists(
            st.tuples(module_names, st.integers(80, 100), st.integers(100, 100)),
            min_size=1, max_size=5,
        )
    )
    @settings(max_examples=50)
    def test_enforce_all_passing(
        self, modules: list[tuple[str, int, int]]
    ) -> None:
        """All passing modules produce passed report."""
        config = EnforcementConfig(
            default_threshold=CoverageThreshold(line_threshold=80.0, branch_threshold=0.0, function_threshold=0.0))
        enforcer = CoverageEnforcer(config)
        metrics_list = [
            CoverageMetrics(module=m, lines_covered=c, lines_total=t)
            for m, c, t in modules
        ]
        report = enforcer.enforce(metrics_list)
        assert report.result == EnforcementResult.PASSED


class TestParseCoverageJson:
    """Property tests for parse_coverage_json."""

    def test_empty_data(self) -> None:
        """Empty data returns empty list."""
        result = parse_coverage_json({})
        assert result == []

    @given(
        filepath=module_names,
        covered=positive_ints,
        total=st.integers(min_value=1, max_value=1000),
    )
    @settings(max_examples=100)
    def test_parse_single_file(self, filepath: str, covered: int, total: int) -> None:
        """Single file is parsed correctly."""
        assume(covered <= total)
        data = {
            "files": {
                filepath: {
                    "summary": {
                        "covered_lines": covered,
                        "num_statements": total,
                    }
                }
            }
        }
        result = parse_coverage_json(data)
        assert len(result) == 1
        assert result[0].module == filepath
        assert result[0].lines_covered == covered
        assert result[0].lines_total == total


class TestCreateDefaultConfig:
    """Property tests for create_default_config."""

    def test_default_config_valid(self) -> None:
        """Default config has valid thresholds."""
        config = create_default_config()
        assert config.default_threshold.line_threshold == 80.0
        assert config.default_threshold.branch_threshold == 70.0
        assert len(config.exclude_patterns) > 0
