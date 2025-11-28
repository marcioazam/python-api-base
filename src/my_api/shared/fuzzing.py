"""Fuzzing Integration Module.

Provides utilities for fuzz testing with corpus management
and integration with fuzzing libraries.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, TypeVar
import hashlib
import json
import base64


T = TypeVar("T")


class FuzzingStatus(Enum):
    """Status of a fuzzing run."""

    RUNNING = "running"
    COMPLETED = "completed"
    CRASHED = "crashed"
    TIMEOUT = "timeout"
    STOPPED = "stopped"


class CrashType(Enum):
    """Types of crashes found during fuzzing."""

    ASSERTION = "assertion"
    EXCEPTION = "exception"
    TIMEOUT = "timeout"
    MEMORY = "memory"
    SEGFAULT = "segfault"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class FuzzInput:
    """Represents a fuzz test input."""

    data: bytes
    source: str = "generated"
    timestamp: datetime = field(default_factory=datetime.now)

    @property
    def hash(self) -> str:
        """Get SHA256 hash of input data."""
        return hashlib.sha256(self.data).hexdigest()

    @property
    def size(self) -> int:
        """Get size of input in bytes."""
        return len(self.data)

    def to_base64(self) -> str:
        """Encode data as base64."""
        return base64.b64encode(self.data).decode("utf-8")

    @classmethod
    def from_base64(cls, encoded: str, source: str = "decoded") -> "FuzzInput":
        """Create from base64 encoded string."""
        data = base64.b64decode(encoded)
        return cls(data=data, source=source)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "data_b64": self.to_base64(),
            "hash": self.hash,
            "size": self.size,
            "source": self.source,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class CrashInfo:
    """Information about a crash found during fuzzing."""

    input_data: FuzzInput
    crash_type: CrashType
    message: str
    stack_trace: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    minimized: bool = False

    @property
    def crash_id(self) -> str:
        """Generate unique crash ID."""
        content = f"{self.crash_type.value}:{self.message}:{self.input_data.hash}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "crash_id": self.crash_id,
            "input": self.input_data.to_dict(),
            "crash_type": self.crash_type.value,
            "message": self.message,
            "stack_trace": self.stack_trace,
            "timestamp": self.timestamp.isoformat(),
            "minimized": self.minimized,
        }


@dataclass
class CoverageInfo:
    """Code coverage information from fuzzing."""

    lines_covered: int = 0
    lines_total: int = 0
    branches_covered: int = 0
    branches_total: int = 0
    functions_covered: int = 0
    functions_total: int = 0

    @property
    def line_coverage(self) -> float:
        """Get line coverage percentage."""
        if self.lines_total == 0:
            return 0.0
        return (self.lines_covered / self.lines_total) * 100

    @property
    def branch_coverage(self) -> float:
        """Get branch coverage percentage."""
        if self.branches_total == 0:
            return 0.0
        return (self.branches_covered / self.branches_total) * 100

    def merge(self, other: "CoverageInfo") -> "CoverageInfo":
        """Merge with another coverage info."""
        return CoverageInfo(
            lines_covered=max(self.lines_covered, other.lines_covered),
            lines_total=max(self.lines_total, other.lines_total),
            branches_covered=max(self.branches_covered, other.branches_covered),
            branches_total=max(self.branches_total, other.branches_total),
            functions_covered=max(self.functions_covered, other.functions_covered),
            functions_total=max(self.functions_total, other.functions_total),
        )


@dataclass
class FuzzingStats:
    """Statistics from a fuzzing run."""

    total_inputs: int = 0
    unique_inputs: int = 0
    crashes_found: int = 0
    timeouts: int = 0
    executions_per_second: float = 0.0
    coverage: CoverageInfo = field(default_factory=CoverageInfo)
    start_time: datetime = field(default_factory=datetime.now)
    end_time: datetime | None = None

    @property
    def duration_seconds(self) -> float:
        """Get duration in seconds."""
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    def record_input(self, is_unique: bool = False) -> None:
        """Record an input execution."""
        self.total_inputs += 1
        if is_unique:
            self.unique_inputs += 1

    def record_crash(self) -> None:
        """Record a crash."""
        self.crashes_found += 1

    def record_timeout(self) -> None:
        """Record a timeout."""
        self.timeouts += 1

    def update_exec_speed(self) -> None:
        """Update executions per second."""
        duration = self.duration_seconds
        if duration > 0:
            self.executions_per_second = self.total_inputs / duration


@dataclass
class FuzzingConfig:
    """Configuration for fuzzing."""

    max_iterations: int = 10000
    timeout_seconds: float = 1.0
    max_input_size: int = 4096
    min_input_size: int = 1
    corpus_dir: Path = field(default_factory=lambda: Path("corpus"))
    crashes_dir: Path = field(default_factory=lambda: Path("crashes"))
    seed: int | None = None
    minimize_crashes: bool = True
    coverage_guided: bool = True

    def validate(self) -> list[str]:
        """Validate configuration."""
        errors: list[str] = []
        if self.max_iterations < 1:
            errors.append("max_iterations must be >= 1")
        if self.timeout_seconds <= 0:
            errors.append("timeout_seconds must be > 0")
        if self.max_input_size < self.min_input_size:
            errors.append("max_input_size must be >= min_input_size")
        if self.min_input_size < 0:
            errors.append("min_input_size must be >= 0")
        return errors


class CorpusManager:
    """Manages fuzzing corpus (seed inputs)."""

    def __init__(self, corpus_dir: Path) -> None:
        self._corpus_dir = corpus_dir
        self._inputs: dict[str, FuzzInput] = {}
        self._load_corpus()

    def _load_corpus(self) -> None:
        """Load corpus from disk."""
        if not self._corpus_dir.exists():
            self._corpus_dir.mkdir(parents=True, exist_ok=True)
            return
        for file_path in self._corpus_dir.glob("*"):
            if file_path.is_file():
                try:
                    data = file_path.read_bytes()
                    fuzz_input = FuzzInput(data=data, source="corpus")
                    self._inputs[fuzz_input.hash] = fuzz_input
                except OSError:
                    pass

    def add(self, fuzz_input: FuzzInput) -> bool:
        """Add input to corpus. Returns True if new."""
        if fuzz_input.hash in self._inputs:
            return False
        self._inputs[fuzz_input.hash] = fuzz_input
        self._save_input(fuzz_input)
        return True

    def _save_input(self, fuzz_input: FuzzInput) -> None:
        """Save input to disk."""
        file_path = self._corpus_dir / fuzz_input.hash[:16]
        file_path.write_bytes(fuzz_input.data)

    def get_all(self) -> list[FuzzInput]:
        """Get all corpus inputs."""
        return list(self._inputs.values())

    def get_by_hash(self, hash_prefix: str) -> FuzzInput | None:
        """Get input by hash prefix."""
        for h, inp in self._inputs.items():
            if h.startswith(hash_prefix):
                return inp
        return None

    def size(self) -> int:
        """Get corpus size."""
        return len(self._inputs)

    def clear(self) -> None:
        """Clear corpus."""
        self._inputs.clear()
        for file_path in self._corpus_dir.glob("*"):
            if file_path.is_file():
                file_path.unlink()


class CrashManager:
    """Manages crash inputs and deduplication."""

    def __init__(self, crashes_dir: Path) -> None:
        self._crashes_dir = crashes_dir
        self._crashes: dict[str, CrashInfo] = {}
        self._crashes_dir.mkdir(parents=True, exist_ok=True)

    def add(self, crash: CrashInfo) -> bool:
        """Add crash. Returns True if new."""
        if crash.crash_id in self._crashes:
            return False
        self._crashes[crash.crash_id] = crash
        self._save_crash(crash)
        return True

    def _save_crash(self, crash: CrashInfo) -> None:
        """Save crash to disk."""
        crash_dir = self._crashes_dir / crash.crash_id
        crash_dir.mkdir(exist_ok=True)
        (crash_dir / "input").write_bytes(crash.input_data.data)
        (crash_dir / "info.json").write_text(json.dumps(crash.to_dict(), indent=2))

    def get_all(self) -> list[CrashInfo]:
        """Get all crashes."""
        return list(self._crashes.values())

    def get_by_type(self, crash_type: CrashType) -> list[CrashInfo]:
        """Get crashes by type."""
        return [c for c in self._crashes.values() if c.crash_type == crash_type]

    def count(self) -> int:
        """Get crash count."""
        return len(self._crashes)


class InputMutator:
    """Mutates inputs for fuzzing."""

    def __init__(self, seed: int | None = None) -> None:
        import random
        self._rng = random.Random(seed)

    def mutate(self, data: bytes) -> bytes:
        """Apply random mutation to data."""
        if not data:
            return bytes([self._rng.randint(0, 255)])
        mutation = self._rng.choice([
            self._bit_flip,
            self._byte_flip,
            self._insert_byte,
            self._delete_byte,
            self._swap_bytes,
            self._duplicate_chunk,
        ])
        return mutation(data)

    def _bit_flip(self, data: bytes) -> bytes:
        """Flip a random bit."""
        data_list = list(data)
        pos = self._rng.randint(0, len(data_list) - 1)
        bit = self._rng.randint(0, 7)
        data_list[pos] ^= (1 << bit)
        return bytes(data_list)

    def _byte_flip(self, data: bytes) -> bytes:
        """Flip a random byte."""
        data_list = list(data)
        pos = self._rng.randint(0, len(data_list) - 1)
        data_list[pos] = self._rng.randint(0, 255)
        return bytes(data_list)

    def _insert_byte(self, data: bytes) -> bytes:
        """Insert a random byte."""
        pos = self._rng.randint(0, len(data))
        new_byte = bytes([self._rng.randint(0, 255)])
        return data[:pos] + new_byte + data[pos:]

    def _delete_byte(self, data: bytes) -> bytes:
        """Delete a random byte."""
        if len(data) <= 1:
            return data
        pos = self._rng.randint(0, len(data) - 1)
        return data[:pos] + data[pos + 1:]

    def _swap_bytes(self, data: bytes) -> bytes:
        """Swap two random bytes."""
        if len(data) < 2:
            return data
        data_list = list(data)
        pos1 = self._rng.randint(0, len(data_list) - 1)
        pos2 = self._rng.randint(0, len(data_list) - 1)
        data_list[pos1], data_list[pos2] = data_list[pos2], data_list[pos1]
        return bytes(data_list)

    def _duplicate_chunk(self, data: bytes) -> bytes:
        """Duplicate a chunk of data."""
        if len(data) < 2:
            return data + data
        start = self._rng.randint(0, len(data) - 1)
        length = self._rng.randint(1, min(10, len(data) - start))
        chunk = data[start:start + length]
        insert_pos = self._rng.randint(0, len(data))
        return data[:insert_pos] + chunk + data[insert_pos:]


class InputMinimizer:
    """Minimizes crash-inducing inputs."""

    def __init__(self, target: Callable[[bytes], None]) -> None:
        self._target = target

    def minimize(self, crash_input: FuzzInput) -> FuzzInput:
        """Minimize input while preserving crash."""
        data = crash_input.data
        if len(data) <= 1:
            return crash_input
        minimized = self._binary_minimize(data)
        minimized = self._byte_minimize(minimized)
        return FuzzInput(data=minimized, source="minimized")

    def _binary_minimize(self, data: bytes) -> bytes:
        """Binary search minimization."""
        if len(data) <= 1:
            return data
        mid = len(data) // 2
        first_half = data[:mid]
        second_half = data[mid:]
        if self._still_crashes(first_half):
            return self._binary_minimize(first_half)
        if self._still_crashes(second_half):
            return self._binary_minimize(second_half)
        return data

    def _byte_minimize(self, data: bytes) -> bytes:
        """Remove bytes one at a time."""
        result = data
        i = 0
        while i < len(result):
            candidate = result[:i] + result[i + 1:]
            if candidate and self._still_crashes(candidate):
                result = candidate
            else:
                i += 1
        return result

    def _still_crashes(self, data: bytes) -> bool:
        """Check if data still causes crash."""
        try:
            self._target(data)
            return False
        except Exception:
            return True


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
        self._stats.end_time = datetime.now()
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
            base = corpus_inputs[
                self._stats.total_inputs % len(corpus_inputs)
            ]
            data = self._mutator.mutate(base.data)
        else:
            import random
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
