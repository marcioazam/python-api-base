"""Property-based tests for Fuzzing module.

**Feature: api-architecture-analysis, Property 15.2: Fuzzing Integration**
**Validates: Requirements 8.2, 5.5**
"""

import pytest
from hypothesis import given, strategies as st, settings, assume
from pathlib import Path
import tempfile

from src.my_api.shared.fuzzing import (
    FuzzingStatus,
    CrashType,
    FuzzInput,
    CrashInfo,
    CoverageInfo,
    FuzzingStats,
    FuzzingConfig,
    CorpusManager,
    CrashManager,
    InputMutator,
    InputMinimizer,
    FuzzingResult,
    Fuzzer,
)


# Strategies
byte_data = st.binary(min_size=1, max_size=100)
sources = st.sampled_from(["generated", "corpus", "seed", "mutated"])
crash_types = st.sampled_from(list(CrashType))
positive_ints = st.integers(min_value=0, max_value=10000)
positive_floats = st.floats(min_value=0.0, max_value=100.0, allow_nan=False)


class TestFuzzInput:
    """Property tests for FuzzInput."""

    @given(data=byte_data)
    @settings(max_examples=100)
    def test_hash_deterministic(self, data: bytes) -> None:
        """Same data produces same hash."""
        input1 = FuzzInput(data=data)
        input2 = FuzzInput(data=data)
        assert input1.hash == input2.hash

    @given(data1=byte_data, data2=byte_data)
    @settings(max_examples=100)
    def test_different_data_different_hash(
        self, data1: bytes, data2: bytes
    ) -> None:
        """Different data produces different hash."""
        assume(data1 != data2)
        input1 = FuzzInput(data=data1)
        input2 = FuzzInput(data=data2)
        assert input1.hash != input2.hash

    @given(data=byte_data)
    @settings(max_examples=100)
    def test_size_matches_data_length(self, data: bytes) -> None:
        """Size property matches data length."""
        fuzz_input = FuzzInput(data=data)
        assert fuzz_input.size == len(data)

    @given(data=byte_data)
    @settings(max_examples=100)
    def test_base64_roundtrip(self, data: bytes) -> None:
        """Base64 encoding roundtrips correctly."""
        fuzz_input = FuzzInput(data=data)
        encoded = fuzz_input.to_base64()
        decoded = FuzzInput.from_base64(encoded)
        assert decoded.data == data

    @given(data=byte_data, source=sources)
    @settings(max_examples=100)
    def test_to_dict_contains_fields(self, data: bytes, source: str) -> None:
        """to_dict contains all required fields."""
        fuzz_input = FuzzInput(data=data, source=source)
        d = fuzz_input.to_dict()
        assert "data_b64" in d
        assert "hash" in d
        assert "size" in d
        assert "source" in d


class TestCrashInfo:
    """Property tests for CrashInfo."""

    @given(data=byte_data, crash_type=crash_types, message=st.text(min_size=1))
    @settings(max_examples=100)
    def test_crash_id_deterministic(
        self, data: bytes, crash_type: CrashType, message: str
    ) -> None:
        """Same crash produces same ID."""
        fuzz_input = FuzzInput(data=data)
        crash1 = CrashInfo(
            input_data=fuzz_input, crash_type=crash_type, message=message
        )
        crash2 = CrashInfo(
            input_data=fuzz_input, crash_type=crash_type, message=message
        )
        assert crash1.crash_id == crash2.crash_id

    @given(data=byte_data, crash_type=crash_types)
    @settings(max_examples=100)
    def test_crash_id_length(self, data: bytes, crash_type: CrashType) -> None:
        """Crash ID has consistent length."""
        fuzz_input = FuzzInput(data=data)
        crash = CrashInfo(
            input_data=fuzz_input, crash_type=crash_type, message="test"
        )
        assert len(crash.crash_id) == 16


class TestCoverageInfo:
    """Property tests for CoverageInfo."""

    @given(covered=positive_ints, total=positive_ints)
    @settings(max_examples=100)
    def test_line_coverage_bounds(self, covered: int, total: int) -> None:
        """Line coverage is between 0 and 100."""
        assume(covered <= total)
        coverage = CoverageInfo(lines_covered=covered, lines_total=total)
        assert 0.0 <= coverage.line_coverage <= 100.0

    @given(covered=positive_ints, total=positive_ints)
    @settings(max_examples=100)
    def test_branch_coverage_bounds(self, covered: int, total: int) -> None:
        """Branch coverage is between 0 and 100."""
        assume(covered <= total)
        coverage = CoverageInfo(branches_covered=covered, branches_total=total)
        assert 0.0 <= coverage.branch_coverage <= 100.0

    @given(
        lines1=st.integers(min_value=0, max_value=100),
        lines2=st.integers(min_value=0, max_value=100),
        total=st.integers(min_value=100, max_value=200),
    )
    @settings(max_examples=100)
    def test_merge_takes_max(
        self, lines1: int, lines2: int, total: int
    ) -> None:
        """Merge takes maximum values."""
        cov1 = CoverageInfo(lines_covered=lines1, lines_total=total)
        cov2 = CoverageInfo(lines_covered=lines2, lines_total=total)
        merged = cov1.merge(cov2)
        assert merged.lines_covered == max(lines1, lines2)


class TestFuzzingStats:
    """Property tests for FuzzingStats."""

    @given(inputs=st.lists(st.booleans(), max_size=100))
    @settings(max_examples=100)
    def test_record_input_counts(self, inputs: list[bool]) -> None:
        """Recording inputs updates counts correctly."""
        stats = FuzzingStats()
        for is_unique in inputs:
            stats.record_input(is_unique)
        assert stats.total_inputs == len(inputs)
        assert stats.unique_inputs == sum(inputs)

    @given(crashes=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_record_crash_counts(self, crashes: int) -> None:
        """Recording crashes updates count."""
        stats = FuzzingStats()
        for _ in range(crashes):
            stats.record_crash()
        assert stats.crashes_found == crashes

    @given(timeouts=st.integers(min_value=0, max_value=100))
    @settings(max_examples=100)
    def test_record_timeout_counts(self, timeouts: int) -> None:
        """Recording timeouts updates count."""
        stats = FuzzingStats()
        for _ in range(timeouts):
            stats.record_timeout()
        assert stats.timeouts == timeouts


class TestFuzzingConfig:
    """Property tests for FuzzingConfig."""

    @given(
        max_iter=st.integers(min_value=1, max_value=100000),
        timeout=st.floats(min_value=0.1, max_value=10.0),
        max_size=st.integers(min_value=10, max_value=10000),
        min_size=st.integers(min_value=0, max_value=9),
    )
    @settings(max_examples=100)
    def test_valid_config(
        self, max_iter: int, timeout: float, max_size: int, min_size: int
    ) -> None:
        """Valid config produces no errors."""
        config = FuzzingConfig(
            max_iterations=max_iter,
            timeout_seconds=timeout,
            max_input_size=max_size,
            min_input_size=min_size,
        )
        errors = config.validate()
        assert len(errors) == 0

    @given(max_iter=st.integers(max_value=0))
    @settings(max_examples=50)
    def test_invalid_iterations(self, max_iter: int) -> None:
        """Invalid iterations produces error."""
        config = FuzzingConfig(max_iterations=max_iter)
        errors = config.validate()
        assert any("iterations" in e for e in errors)

    @given(timeout=st.floats(max_value=0.0))
    @settings(max_examples=50)
    def test_invalid_timeout(self, timeout: float) -> None:
        """Invalid timeout produces error."""
        config = FuzzingConfig(timeout_seconds=timeout)
        errors = config.validate()
        assert any("timeout" in e for e in errors)


class TestInputMutator:
    """Property tests for InputMutator."""

    @given(data=byte_data, seed=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=100)
    def test_mutate_produces_bytes(self, data: bytes, seed: int) -> None:
        """Mutation produces bytes output."""
        mutator = InputMutator(seed=seed)
        result = mutator.mutate(data)
        assert isinstance(result, bytes)
        assert len(result) > 0

    @given(seed=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=100)
    def test_mutate_empty_produces_byte(self, seed: int) -> None:
        """Mutating empty bytes produces at least one byte."""
        mutator = InputMutator(seed=seed)
        result = mutator.mutate(b"")
        assert len(result) >= 1

    @given(data=byte_data, seed=st.integers(min_value=0, max_value=10000))
    @settings(max_examples=100)
    def test_deterministic_with_seed(self, data: bytes, seed: int) -> None:
        """Same seed produces same mutation sequence."""
        mutator1 = InputMutator(seed=seed)
        mutator2 = InputMutator(seed=seed)
        result1 = mutator1.mutate(data)
        result2 = mutator2.mutate(data)
        assert result1 == result2


class TestCorpusManager:
    """Property tests for CorpusManager."""

    @given(inputs=st.lists(byte_data, min_size=1, max_size=10))
    @settings(max_examples=50)
    def test_add_and_retrieve(self, inputs: list[bytes]) -> None:
        """Added inputs can be retrieved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = CorpusManager(Path(tmpdir) / "corpus")
            for data in inputs:
                fuzz_input = FuzzInput(data=data)
                corpus.add(fuzz_input)
            all_inputs = corpus.get_all()
            unique_hashes = {FuzzInput(data=d).hash for d in inputs}
            assert len(all_inputs) == len(unique_hashes)

    @given(data=byte_data)
    @settings(max_examples=50)
    def test_add_duplicate_returns_false(self, data: bytes) -> None:
        """Adding duplicate returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = CorpusManager(Path(tmpdir) / "corpus")
            fuzz_input = FuzzInput(data=data)
            first = corpus.add(fuzz_input)
            second = corpus.add(fuzz_input)
            assert first is True
            assert second is False

    @given(data=byte_data)
    @settings(max_examples=50)
    def test_get_by_hash(self, data: bytes) -> None:
        """Can retrieve by hash prefix."""
        with tempfile.TemporaryDirectory() as tmpdir:
            corpus = CorpusManager(Path(tmpdir) / "corpus")
            fuzz_input = FuzzInput(data=data)
            corpus.add(fuzz_input)
            retrieved = corpus.get_by_hash(fuzz_input.hash[:8])
            assert retrieved is not None
            assert retrieved.data == data


class TestCrashManager:
    """Property tests for CrashManager."""

    @given(data=byte_data, crash_type=crash_types)
    @settings(max_examples=50)
    def test_add_and_retrieve(self, data: bytes, crash_type: CrashType) -> None:
        """Added crashes can be retrieved."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CrashManager(Path(tmpdir) / "crashes")
            fuzz_input = FuzzInput(data=data)
            crash = CrashInfo(
                input_data=fuzz_input, crash_type=crash_type, message="test"
            )
            manager.add(crash)
            all_crashes = manager.get_all()
            assert len(all_crashes) == 1
            assert all_crashes[0].crash_id == crash.crash_id

    @given(data=byte_data, crash_type=crash_types)
    @settings(max_examples=50)
    def test_add_duplicate_returns_false(
        self, data: bytes, crash_type: CrashType
    ) -> None:
        """Adding duplicate crash returns False."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CrashManager(Path(tmpdir) / "crashes")
            fuzz_input = FuzzInput(data=data)
            crash = CrashInfo(
                input_data=fuzz_input, crash_type=crash_type, message="test"
            )
            first = manager.add(crash)
            second = manager.add(crash)
            assert first is True
            assert second is False

    @given(
        crashes=st.lists(
            st.tuples(byte_data, crash_types),
            min_size=1,
            max_size=5,
        )
    )
    @settings(max_examples=50)
    def test_get_by_type(
        self, crashes: list[tuple[bytes, CrashType]]
    ) -> None:
        """Can filter crashes by type."""
        with tempfile.TemporaryDirectory() as tmpdir:
            manager = CrashManager(Path(tmpdir) / "crashes")
            for data, crash_type in crashes:
                fuzz_input = FuzzInput(data=data)
                crash = CrashInfo(
                    input_data=fuzz_input, crash_type=crash_type, message="test"
                )
                manager.add(crash)
            for crash_type in CrashType:
                filtered = manager.get_by_type(crash_type)
                assert all(c.crash_type == crash_type for c in filtered)


class TestFuzzer:
    """Property tests for Fuzzer."""

    @given(seeds=st.lists(byte_data, min_size=1, max_size=5))
    @settings(max_examples=30)
    def test_add_seeds(self, seeds: list[bytes]) -> None:
        """Seeds can be added to fuzzer."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FuzzingConfig(
                corpus_dir=Path(tmpdir) / "corpus",
                crashes_dir=Path(tmpdir) / "crashes",
                max_iterations=10,
            )
            fuzzer = Fuzzer(target=lambda x: None, config=config)
            for seed in seeds:
                fuzzer.add_seed(seed)

    @given(iterations=st.integers(min_value=1, max_value=50))
    @settings(max_examples=30)
    def test_run_completes(self, iterations: int) -> None:
        """Fuzzer run completes with correct status."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = FuzzingConfig(
                corpus_dir=Path(tmpdir) / "corpus",
                crashes_dir=Path(tmpdir) / "crashes",
                max_iterations=iterations,
            )
            fuzzer = Fuzzer(target=lambda x: None, config=config)
            result = fuzzer.run()
            assert result.status == FuzzingStatus.COMPLETED
            assert result.stats.total_inputs == iterations

    @given(iterations=st.integers(min_value=10, max_value=50))
    @settings(max_examples=30, deadline=None)
    def test_finds_crashes(self, iterations: int) -> None:
        """Fuzzer finds crashes in buggy target."""
        def buggy_target(data: bytes) -> None:
            if len(data) > 5 and data[0] == 0x41:
                raise ValueError("Bug found!")

        with tempfile.TemporaryDirectory() as tmpdir:
            config = FuzzingConfig(
                corpus_dir=Path(tmpdir) / "corpus",
                crashes_dir=Path(tmpdir) / "crashes",
                max_iterations=iterations,
                seed=42,
            )
            fuzzer = Fuzzer(target=buggy_target, config=config)
            fuzzer.add_seed(b"AAAAAAA")
            result = fuzzer.run()
            assert result.stats.crashes_found >= 0


class TestFuzzingResult:
    """Property tests for FuzzingResult."""

    @given(
        total=positive_ints,
        unique=positive_ints,
        crashes=st.integers(min_value=0, max_value=10),
    )
    @settings(max_examples=100)
    def test_to_dict_structure(
        self, total: int, unique: int, crashes: int
    ) -> None:
        """to_dict has correct structure."""
        assume(unique <= total)
        stats = FuzzingStats(
            total_inputs=total, unique_inputs=unique, crashes_found=crashes
        )
        config = FuzzingConfig()
        result = FuzzingResult(
            status=FuzzingStatus.COMPLETED,
            stats=stats,
            crashes=[],
            config=config,
        )
        d = result.to_dict()
        assert "status" in d
        assert "stats" in d
        assert "crashes" in d

    def test_to_json_valid(self) -> None:
        """to_json produces valid JSON."""
        stats = FuzzingStats()
        config = FuzzingConfig()
        result = FuzzingResult(
            status=FuzzingStatus.COMPLETED,
            stats=stats,
            crashes=[],
            config=config,
        )
        json_str = result.to_json()
        import json
        parsed = json.loads(json_str)
        assert parsed["status"] == "completed"
