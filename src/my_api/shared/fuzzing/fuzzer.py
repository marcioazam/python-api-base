"""Main fuzzer implementation.

**Feature: code-review-refactoring, Task 16.3: Refactor fuzzing.py**
**Validates: Requirements 5.3**
"""

import json
import random
from dataclasses import dataclass
from datetime import datetime, UTC
from typing import Any
from collections.abc import Callable

from .config import FuzzingConfig
from .corpus import CorpusManager, CrashManager
from .enums import CrashType, FuzzingStatus
from .models import CrashInfo, FuzzInput, FuzzingStats
from .mutator import InputMutator


@dataclass
class FuzzingResult:
    """Result of a fuzzing run."""

    status: FuzzingStatus
    stats: FuzzingStats
    crashes: list[CrashInfo]
    config: FuzzingConfig

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "status": self.status.value,
            "stats": {
                "total_inputs": self.stats.total_inputs,
                "unique_inputs": self.stats.unique_inputs,
                "crashes_found": self.stats.crashes_found,
                "duration_seconds": self.stats.duration_seconds,
                "exec_per_second": self.stats.executions_per_second,
            },
            "crashes": [c.to_dict() for c in self.crashes],
        }

    def to_json(self) -> str:
        """Convert to JSON."""
        return json.dumps(self.to_dict(), indent=2)


class Fuzzer:
    """Main fuzzer class."""

    def __init__(
        self,
        target: Callable[[bytes], None],
        config: FuzzingConfig,
    ) -> None:
        self._target = target
        self._config = config
        self._corpus = CorpusManager(config.corpus_dir)
        self._crashes = CrashManager(config.crashes_dir)
        self._mutator = InputMutator(config.seed)
        self._stats = FuzzingStats()
        self._status = FuzzingStatus.STOPPED

    @property
    def config(self) -> FuzzingConfig:
        """Get configuration."""
        return self._config

    @property
    def stats(self) -> FuzzingStats:
        """Get current stats."""
        return self._stats

    @property
    def status(self) -> FuzzingStatus:
        """Get current status."""
        return self._status

    def add_seed(self, data: bytes) -> bool:
        """Add seed input to corpus."""
        fuzz_input = FuzzInput(data=data, source="seed")
        return self._corpus.add(fuzz_input)

    def run(self) -> FuzzingResult:
        """Run fuzzing campaign."""
        self._status = FuzzingStatus.RUNNING
        self._stats = FuzzingStats()
        try:
            for _ in range(self._config.max_iterations):
                if self._status != FuzzingStatus.RUNNING:
                    break
                self._fuzz_one()
            self._status = FuzzingStatus.COMPLETED
        except Exception:
            self._status = FuzzingStatus.CRASHED
        self._stats.end_time = datetime.now(UTC)
        self._stats.update_exec_speed()
        return FuzzingResult(
            status=self._status,
            stats=self._stats,
            crashes=self._crashes.get_all(),
            config=self._config,
        )

    def _fuzz_one(self) -> None:
        """Execute one fuzzing iteration."""
        corpus_inputs = self._corpus.get_all()
        if corpus_inputs:
            base = corpus_inputs[self._stats.total_inputs % len(corpus_inputs)]
            data = self._mutator.mutate(base.data)
        else:
            size = random.randint(
                self._config.min_input_size,
                self._config.max_input_size,
            )
            data = bytes(random.randint(0, 255) for _ in range(size))
        fuzz_input = FuzzInput(data=data, source="mutated")
        is_new = self._corpus.add(fuzz_input)
        self._stats.record_input(is_new)
        try:
            self._target(data)
        except Exception as e:
            crash = CrashInfo(
                input_data=fuzz_input,
                crash_type=CrashType.EXCEPTION,
                message=str(e),
            )
            if self._crashes.add(crash):
                self._stats.record_crash()

    def stop(self) -> None:
        """Stop fuzzing."""
        self._status = FuzzingStatus.STOPPED
