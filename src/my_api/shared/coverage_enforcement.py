"""Coverage Enforcement Module.

Provides utilities for enforcing per-module coverage thresholds
and branch coverage requirements.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import json


class CoverageType(Enum):
    """Types of coverage metrics."""
    LINE = "line"
    BRANCH = "branch"
    FUNCTION = "function"
    STATEMENT = "statement"


class EnforcementResult(Enum):
    """Result of coverage enforcement."""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class CoverageMetrics:
    """Coverage metrics for a module."""
    module: str
    lines_covered: int = 0
    lines_total: int = 0
    branches_covered: int = 0
    branches_total: int = 0
    functions_covered: int = 0
    functions_total: int = 0

    @property
    def line_coverage(self) -> float:
        return (self.lines_covered / self.lines_total * 100) if self.lines_total > 0 else 0.0

    @property
    def branch_coverage(self) -> float:
        return (self.branches_covered / self.branches_total * 100) if self.branches_total > 0 else 0.0

    @property
    def function_coverage(self) -> float:
        return (self.functions_covered / self.functions_total * 100) if self.functions_total > 0 else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {"module": self.module, "line_coverage": self.line_coverage,
                "branch_coverage": self.branch_coverage, "function_coverage": self.function_coverage,
                "lines": f"{self.lines_covered}/{self.lines_total}",
                "branches": f"{self.branches_covered}/{self.branches_total}",
                "functions": f"{self.functions_covered}/{self.functions_total}"}


@dataclass
class CoverageThreshold:
    """Coverage threshold configuration."""
    line_threshold: float = 80.0
    branch_threshold: float = 70.0
    function_threshold: float = 80.0
    fail_under: bool = True

    def check_line(self, coverage: float) -> bool:
        return coverage >= self.line_threshold

    def check_branch(self, coverage: float) -> bool:
        return coverage >= self.branch_threshold

    def check_function(self, coverage: float) -> bool:
        return coverage >= self.function_threshold

    def check_all(self, metrics: CoverageMetrics) -> bool:
        return (self.check_line(metrics.line_coverage) and
                self.check_branch(metrics.branch_coverage) and
                self.check_function(metrics.function_coverage))


@dataclass
class ModuleThreshold:
    """Per-module threshold configuration."""
    pattern: str
    threshold: CoverageThreshold
    enabled: bool = True

    def matches(self, module: str) -> bool:
        if "*" in self.pattern:
            prefix = self.pattern.rstrip("*")
            return module.startswith(prefix)
        return module == self.pattern


@dataclass
class EnforcementConfig:
    """Configuration for coverage enforcement."""
    default_threshold: CoverageThreshold = field(default_factory=CoverageThreshold)
    module_thresholds: list[ModuleThreshold] = field(default_factory=list)
    exclude_patterns: list[str] = field(default_factory=list)
    fail_on_missing: bool = False

    def get_threshold(self, module: str) -> CoverageThreshold:
        for mt in self.module_thresholds:
            if mt.enabled and mt.matches(module):
                return mt.threshold
        return self.default_threshold

    def is_excluded(self, module: str) -> bool:
        for pattern in self.exclude_patterns:
            if "*" in pattern:
                prefix = pattern.rstrip("*")
                if module.startswith(prefix):
                    return True
            elif module == pattern:
                return True
        return False

    def add_module_threshold(self, pattern: str, line: float = 80.0, branch: float = 70.0) -> None:
        threshold = CoverageThreshold(line_threshold=line, branch_threshold=branch)
        self.module_thresholds.append(ModuleThreshold(pattern=pattern, threshold=threshold))


@dataclass
class EnforcementViolation:
    """A coverage threshold violation."""
    module: str
    coverage_type: CoverageType
    actual: float
    required: float
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"module": self.module, "type": self.coverage_type.value,
                "actual": self.actual, "required": self.required, "message": self.message}


@dataclass
class EnforcementReport:
    """Report of coverage enforcement."""
    timestamp: datetime = field(default_factory=datetime.now)
    result: EnforcementResult = EnforcementResult.PASSED
    violations: list[EnforcementViolation] = field(default_factory=list)
    passed_modules: list[str] = field(default_factory=list)
    skipped_modules: list[str] = field(default_factory=list)
    total_line_coverage: float = 0.0
    total_branch_coverage: float = 0.0

    @property
    def has_violations(self) -> bool:
        return len(self.violations) > 0

    @property
    def violation_count(self) -> int:
        return len(self.violations)

    def add_violation(self, violation: EnforcementViolation) -> None:
        self.violations.append(violation)
        self.result = EnforcementResult.FAILED

    def to_dict(self) -> dict[str, Any]:
        return {"timestamp": self.timestamp.isoformat(), "result": self.result.value,
                "violations": [v.to_dict() for v in self.violations],
                "passed_modules": self.passed_modules, "skipped_modules": self.skipped_modules,
                "total_line_coverage": self.total_line_coverage,
                "total_branch_coverage": self.total_branch_coverage}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    def generate_summary(self) -> str:
        lines = ["Coverage Enforcement Report", "=" * 40,
                 f"Result: {self.result.value.upper()}",
                 f"Total Line Coverage: {self.total_line_coverage:.1f}%",
                 f"Total Branch Coverage: {self.total_branch_coverage:.1f}%", ""]
        if self.violations:
            lines.append(f"Violations ({len(self.violations)}):")
            for v in self.violations:
                lines.append(f"  - {v.module}: {v.message}")
        lines.append(f"\nPassed: {len(self.passed_modules)}")
        lines.append(f"Skipped: {len(self.skipped_modules)}")
        return "\n".join(lines)


class CoverageEnforcer:
    """Enforces coverage thresholds."""
    def __init__(self, config: EnforcementConfig | None = None) -> None:
        self._config = config or EnforcementConfig()

    @property
    def config(self) -> EnforcementConfig:
        return self._config

    def check_module(self, metrics: CoverageMetrics) -> list[EnforcementViolation]:
        violations: list[EnforcementViolation] = []
        if self._config.is_excluded(metrics.module):
            return violations
        threshold = self._config.get_threshold(metrics.module)
        if not threshold.check_line(metrics.line_coverage):
            violations.append(EnforcementViolation(
                module=metrics.module, coverage_type=CoverageType.LINE,
                actual=metrics.line_coverage, required=threshold.line_threshold,
                message=f"Line coverage {metrics.line_coverage:.1f}% < {threshold.line_threshold:.1f}%"))
        if not threshold.check_branch(metrics.branch_coverage):
            violations.append(EnforcementViolation(
                module=metrics.module, coverage_type=CoverageType.BRANCH,
                actual=metrics.branch_coverage, required=threshold.branch_threshold,
                message=f"Branch coverage {metrics.branch_coverage:.1f}% < {threshold.branch_threshold:.1f}%"))
        if not threshold.check_function(metrics.function_coverage):
            violations.append(EnforcementViolation(
                module=metrics.module, coverage_type=CoverageType.FUNCTION,
                actual=metrics.function_coverage, required=threshold.function_threshold,
                message=f"Function coverage {metrics.function_coverage:.1f}% < {threshold.function_threshold:.1f}%"))
        return violations

    def enforce(self, all_metrics: list[CoverageMetrics]) -> EnforcementReport:
        report = EnforcementReport()
        total_lines_covered = 0
        total_lines = 0
        total_branches_covered = 0
        total_branches = 0
        for metrics in all_metrics:
            if self._config.is_excluded(metrics.module):
                report.skipped_modules.append(metrics.module)
                continue
            total_lines_covered += metrics.lines_covered
            total_lines += metrics.lines_total
            total_branches_covered += metrics.branches_covered
            total_branches += metrics.branches_total
            violations = self.check_module(metrics)
            if violations:
                for v in violations:
                    report.add_violation(v)
            else:
                report.passed_modules.append(metrics.module)
        report.total_line_coverage = (total_lines_covered / total_lines * 100) if total_lines > 0 else 0.0
        report.total_branch_coverage = (total_branches_covered / total_branches * 100) if total_branches > 0 else 0.0
        return report


def parse_coverage_json(coverage_data: dict[str, Any]) -> list[CoverageMetrics]:
    """Parse coverage.py JSON output."""
    metrics: list[CoverageMetrics] = []
    files = coverage_data.get("files", {})
    for filepath, data in files.items():
        summary = data.get("summary", {})
        metrics.append(CoverageMetrics(
            module=filepath,
            lines_covered=summary.get("covered_lines", 0),
            lines_total=summary.get("num_statements", 0),
            branches_covered=summary.get("covered_branches", 0),
            branches_total=summary.get("num_branches", 0)))
    return metrics


def create_default_config() -> EnforcementConfig:
    """Create default enforcement configuration."""
    config = EnforcementConfig(
        default_threshold=CoverageThreshold(line_threshold=80.0, branch_threshold=70.0),
        exclude_patterns=["*/__pycache__/*", "*/tests/*", "*/.venv/*"])
    return config
