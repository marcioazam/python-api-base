"""mutation_testing configuration."""

from dataclasses import dataclass, field
from .enums import MutationOperator


@dataclass
class MutationConfig:
    """Configuration for mutation testing."""

    source_paths: list[str] = field(default_factory=lambda: ["src"])
    test_paths: list[str] = field(default_factory=lambda: ["tests"])
    exclude_patterns: list[str] = field(default_factory=list)
    operators: list[MutationOperator] = field(
        default_factory=lambda: list(MutationOperator)
    )
    timeout_multiplier: float = 2.0
    parallel: bool = True
    max_workers: int = 4
    min_score_threshold: float = 0.8

    def validate(self) -> list[str]:
        """Validate configuration."""
        errors: list[str] = []
        if not self.source_paths:
            errors.append("source_paths cannot be empty")
        if not self.test_paths:
            errors.append("test_paths cannot be empty")
        if self.timeout_multiplier < 1.0:
            errors.append("timeout_multiplier must be >= 1.0")
        if self.max_workers < 1:
            errors.append("max_workers must be >= 1")
        if not 0.0 <= self.min_score_threshold <= 1.0:
            errors.append("min_score_threshold must be between 0.0 and 1.0")
        return errors
