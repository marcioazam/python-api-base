"""mutation_testing service."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import hashlib
from .enums import MutantStatus, MutationOperator
from .models import MutationReport, MutantLocation
from .config import MutationConfig


@dataclass(frozen=True, slots=True)
class Mutant:
    """Represents a single mutation."""

    id: str
    location: MutantLocation
    operator: str
    original: str
    replacement: str
    status: MutantStatus = MutantStatus.SURVIVED
    test_time_ms: float = 0.0

    @property
    def is_killed(self) -> bool:
        """Check if mutant was killed."""
        return self.status == MutantStatus.KILLED

    @property
    def is_survived(self) -> bool:
        """Check if mutant survived."""
        return self.status == MutantStatus.SURVIVED

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "file": self.location.file,
            "line": self.location.line,
            "operator": self.operator,
            "original": self.original,
            "replacement": self.replacement,
            "status": self.status.value,
            "test_time_ms": self.test_time_ms,
        }

class MutationScoreTracker:
    """Tracks mutation scores over time."""

    def __init__(self, storage_path: Path | None = None) -> None:
        self._storage_path = storage_path or Path(".mutation_history.json")
        self._history: list[dict[str, Any]] = []
        self._load_history()

    def _load_history(self) -> None:
        """Load history from storage."""
        if self._storage_path.exists():
            try:
                with open(self._storage_path, encoding="utf-8") as f:
                    self._history = json.load(f)
            except (json.JSONDecodeError, OSError, UnicodeDecodeError):
                self._history = []

    def _save_history(self) -> None:
        """Save history to storage."""
        with open(self._storage_path, "w", encoding="utf-8") as f:
            json.dump(self._history, f, indent=2)

    def record(self, report: MutationReport) -> None:
        """Record a mutation report."""
        entry = {
            "timestamp": report.timestamp.isoformat(),
            "score": report.total_score,
            "total_mutants": report.total_mutants,
            "modules": {
                k: v.score for k, v in report.modules.items()
            },
        }
        self._history.append(entry)
        self._save_history()

    def get_trend(self, last_n: int = 10) -> list[float]:
        """Get score trend for last N runs."""
        entries = self._history[-last_n:]
        return [e["score"] for e in entries]

    def get_regression(self, current: MutationReport) -> list[str]:
        """Get modules with score regression."""
        if not self._history:
            return []
        last = self._history[-1]
        regressions: list[str] = []
        for module, score in current.modules.items():
            if module in last.get("modules", {}):
                prev_score = last["modules"][module]
                if score.score < prev_score:
                    regressions.append(module)
        return regressions

    def meets_threshold(
        self, report: MutationReport, threshold: float
    ) -> bool:
        """Check if report meets score threshold."""
        return report.total_score >= threshold

class MutationTestRunner:
    """Runner for mutation testing."""

    def __init__(self, config: MutationConfig) -> None:
        self._config = config
        self._tracker = MutationScoreTracker()

    @property
    def config(self) -> MutationConfig:
        """Get configuration."""
        return self._config

    def validate_config(self) -> list[str]:
        """Validate runner configuration."""
        return self._config.validate()

    def check_threshold(self, report: MutationReport) -> bool:
        """Check if report meets threshold."""
        return self._tracker.meets_threshold(
            report, self._config.min_score_threshold
        )

    def get_regressions(self, report: MutationReport) -> list[str]:
        """Get modules with regressions."""
        return self._tracker.get_regression(report)

    def record_results(self, report: MutationReport) -> None:
        """Record results to tracker."""
        self._tracker.record(report)

    def generate_report_summary(self, report: MutationReport) -> str:
        """Generate human-readable summary."""
        lines = [
            "Mutation Testing Report",
            "=" * 40,
            f"Total Score: {report.total_score * 100:.1f}%",
            f"Total Mutants: {report.total_mutants}",
            f"Duration: {report.duration_seconds:.1f}s",
            "",
            "Module Scores:",
        ]
        for module, score in sorted(report.modules.items()):
            lines.append(
                f"  {module}: {score.score_percent:.1f}% "
                f"({score.killed}/{score.total_mutants})"
            )
        if report.survived_mutants:
            lines.extend(["", "Survived Mutants:"])
            for mutant in report.survived_mutants[:10]:
                lines.append(f"  {mutant.location}: {mutant.operator}")
            if len(report.survived_mutants) > 10:
                lines.append(f"  ... and {len(report.survived_mutants) - 10} more")
        return "\n".join(lines)

def generate_mutant_id(
    file: str, line: int, operator: str, replacement: str
) -> str:
    """Generate unique mutant ID."""
    content = f"{file}:{line}:{operator}:{replacement}"
    return hashlib.sha256(content.encode()).hexdigest()[:12]

def create_mutant(
    file: str,
    line: int,
    operator: MutationOperator,
    original: str,
    replacement: str,
    status: MutantStatus = MutantStatus.SURVIVED,
) -> Mutant:
    """Create a mutant instance."""
    mutant_id = generate_mutant_id(file, line, operator.value, replacement)
    location = MutantLocation(file=file, line=line)
    return Mutant(
        id=mutant_id,
        location=location,
        operator=operator.value,
        original=original,
        replacement=replacement,
        status=status,
    )

def get_mutmut_command(config: MutationConfig) -> list[str]:
    """Generate mutmut command from config."""
    cmd = ["mutmut", "run"]
    for path in config.source_paths:
        cmd.extend(["--paths-to-mutate", path])
    for path in config.test_paths:
        cmd.extend(["--tests-dir", path])
    if config.parallel:
        cmd.extend(["--runner", f"pytest -x -n {config.max_workers}"])
    return cmd

def parse_mutmut_results(results_path: Path) -> MutationReport:
    """Parse mutmut results into report."""
    report = MutationReport()
    if not results_path.exists():
        return report
    try:
        with open(results_path, encoding="utf-8") as f:
            data = json.load(f)
        for mutant_data in data.get("mutants", []):
            status = MutantStatus(mutant_data.get("status", "survived"))
            mutant = Mutant(
                id=mutant_data.get("id", ""),
                location=MutantLocation(
                    file=mutant_data.get("file", ""),
                    line=mutant_data.get("line", 0),
                ),
                operator=mutant_data.get("operator", ""),
                original=mutant_data.get("original", ""),
                replacement=mutant_data.get("replacement", ""),
                status=status,
            )
            report.add_mutant(mutant)
    except (json.JSONDecodeError, OSError, KeyError):
        pass
    return report
