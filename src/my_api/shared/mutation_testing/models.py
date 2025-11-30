"""mutation_testing models."""

from __future__ import annotations
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TYPE_CHECKING
import json
from .enums import MutantStatus

if TYPE_CHECKING:
    from .service import Mutant


@dataclass(frozen=True, slots=True)
class MutantLocation:
    """Location of a mutation in source code."""

    file: str
    line: int
    column: int = 0
    end_line: int | None = None
    end_column: int | None = None

    def __str__(self) -> str:
        return f"{self.file}:{self.line}"


@dataclass
class MutationScore:
    """Mutation testing score for a module."""

    module: str
    total_mutants: int = 0
    killed: int = 0
    survived: int = 0
    timeout: int = 0
    skipped: int = 0

    @property
    def score(self) -> float:
        """Calculate mutation score (0.0 to 1.0)."""
        if self.total_mutants == 0:
            return 1.0
        effective = self.total_mutants - self.skipped
        if effective == 0:
            return 1.0
        return self.killed / effective

    @property
    def score_percent(self) -> float:
        """Get score as percentage."""
        return self.score * 100

    def add_mutant(self, status: MutantStatus) -> None:
        """Add mutant result."""
        self.total_mutants += 1
        if status == MutantStatus.KILLED:
            self.killed += 1
        elif status == MutantStatus.SURVIVED:
            self.survived += 1
        elif status == MutantStatus.TIMEOUT:
            self.timeout += 1
        elif status == MutantStatus.SKIPPED:
            self.skipped += 1

@dataclass
class MutationReport:
    """Complete mutation testing report."""

    timestamp: datetime = field(default_factory=datetime.now)
    duration_seconds: float = 0.0
    modules: dict[str, MutationScore] = field(default_factory=dict)
    mutants: list["Mutant"] = field(default_factory=list)
    config: dict[str, Any] = field(default_factory=dict)

    @property
    def total_score(self) -> float:
        """Calculate overall mutation score."""
        total = sum(m.total_mutants for m in self.modules.values())
        killed = sum(m.killed for m in self.modules.values())
        skipped = sum(m.skipped for m in self.modules.values())
        effective = total - skipped
        if effective == 0:
            return 1.0
        return killed / effective

    @property
    def total_mutants(self) -> int:
        """Get total mutant count."""
        return sum(m.total_mutants for m in self.modules.values())

    @property
    def survived_mutants(self) -> list["Mutant"]:
        """Get list of survived mutants."""
        return [m for m in self.mutants if m.is_survived]

    def add_mutant(self, mutant: "Mutant") -> None:
        """Add mutant to report."""
        self.mutants.append(mutant)
        module = mutant.location.file
        if module not in self.modules:
            self.modules[module] = MutationScore(module=module)
        self.modules[module].add_mutant(mutant.status)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "duration_seconds": self.duration_seconds,
            "total_score": self.total_score,
            "total_mutants": self.total_mutants,
            "modules": {
                k: {
                    "score": v.score_percent,
                    "total": v.total_mutants,
                    "killed": v.killed,
                    "survived": v.survived,
                }
                for k, v in self.modules.items()
            },
            "survived": [m.to_dict() for m in self.survived_mutants],
        }

    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=2)
