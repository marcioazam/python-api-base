"""Property-based tests for Mutation Testing module.

**Feature: api-architecture-analysis, Property 15.1: Mutation Testing**
**Validates: Requirements 8.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime

from src.my_app.shared.mutation_testing import (
    MutantStatus,
    MutantLocation,
    Mutant,
    MutationScore,
    MutationReport,
    MutationOperator,
    MutationConfig,
    MutationScoreTracker,
    MutationTestRunner,
    generate_mutant_id,
    create_mutant,
    get_mutmut_command,
)


# Strategies
file_paths = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="/_-."),
    min_size=1,
    max_size=50,
).map(lambda s: s + ".py")

line_numbers = st.integers(min_value=1, max_value=10000)
column_numbers = st.integers(min_value=0, max_value=200)

mutant_statuses = st.sampled_from(list(MutantStatus))
mutation_operators = st.sampled_from(list(MutationOperator))

code_snippets = st.text(min_size=1, max_size=50)

mutant_locations = st.builds(
    MutantLocation,
    file=file_paths,
    line=line_numbers,
    column=column_numbers,
)

scores = st.floats(min_value=0.0, max_value=1.0, allow_nan=False)
positive_ints = st.integers(min_value=0, max_value=1000)


class TestMutantLocation:
    """Property tests for MutantLocation."""

    @given(file=file_paths, line=line_numbers)
    @settings(max_examples=100)
    def test_str_contains_file_and_line(self, file: str, line: int) -> None:
        """String representation contains file and line."""
        location = MutantLocation(file=file, line=line)
        result = str(location)
        assert file in result
        assert str(line) in result

    @given(location=mutant_locations)
    @settings(max_examples=100)
    def test_location_immutable(self, location: MutantLocation) -> None:
        """Location is immutable (frozen dataclass)."""
        with pytest.raises(AttributeError):
            location.line = 999  # type: ignore


class TestMutant:
    """Property tests for Mutant."""

    @given(
        file=file_paths,
        line=line_numbers,
        operator=mutation_operators,
        original=code_snippets,
        replacement=code_snippets,
    )
    @settings(max_examples=100)
    def test_create_mutant(
        self,
        file: str,
        line: int,
        operator: MutationOperator,
        original: str,
        replacement: str,
    ) -> None:
        """Created mutant has correct attributes."""
        mutant = create_mutant(file, line, operator, original, replacement)
        assert mutant.location.file == file
        assert mutant.location.line == line
        assert mutant.operator == operator.value
        assert mutant.original == original
        assert mutant.replacement == replacement

    @given(status=mutant_statuses)
    @settings(max_examples=100)
    def test_is_killed_property(self, status: MutantStatus) -> None:
        """is_killed returns True only for KILLED status."""
        mutant = create_mutant("test.py", 1, MutationOperator.AOR, "a", "b", status)
        assert mutant.is_killed == (status == MutantStatus.KILLED)

    @given(status=mutant_statuses)
    @settings(max_examples=100)
    def test_is_survived_property(self, status: MutantStatus) -> None:
        """is_survived returns True only for SURVIVED status."""
        mutant = create_mutant("test.py", 1, MutationOperator.AOR, "a", "b", status)
        assert mutant.is_survived == (status == MutantStatus.SURVIVED)

    @given(
        file=file_paths,
        line=line_numbers,
        operator=mutation_operators,
        original=code_snippets,
        replacement=code_snippets,
    )
    @settings(max_examples=100)
    def test_to_dict_contains_all_fields(
        self,
        file: str,
        line: int,
        operator: MutationOperator,
        original: str,
        replacement: str,
    ) -> None:
        """to_dict contains all required fields."""
        mutant = create_mutant(file, line, operator, original, replacement)
        d = mutant.to_dict()
        assert "id" in d
        assert "file" in d
        assert "line" in d
        assert "operator" in d
        assert "original" in d
        assert "replacement" in d
        assert "status" in d


class TestMutationScore:
    """Property tests for MutationScore."""

    @given(killed=positive_ints, survived=positive_ints)
    @settings(max_examples=100)
    def test_score_calculation(self, killed: int, survived: int) -> None:
        """Score is killed / total."""
        score = MutationScore(
            module="test",
            total_mutants=killed + survived,
            killed=killed,
            survived=survived,
        )
        if killed + survived > 0:
            expected = killed / (killed + survived)
            assert abs(score.score - expected) < 0.0001
        else:
            assert score.score == 1.0

    @given(killed=positive_ints, survived=positive_ints)
    @settings(max_examples=100)
    def test_score_percent(self, killed: int, survived: int) -> None:
        """Score percent is score * 100."""
        score = MutationScore(
            module="test",
            total_mutants=killed + survived,
            killed=killed,
            survived=survived,
        )
        assert abs(score.score_percent - score.score * 100) < 0.0001

    @given(statuses=st.lists(mutant_statuses, min_size=1, max_size=50))
    @settings(max_examples=100)
    def test_add_mutant_counts(self, statuses: list[MutantStatus]) -> None:
        """Adding mutants updates counts correctly."""
        score = MutationScore(module="test")
        for status in statuses:
            score.add_mutant(status)
        assert score.total_mutants == len(statuses)
        assert score.killed == statuses.count(MutantStatus.KILLED)
        assert score.survived == statuses.count(MutantStatus.SURVIVED)

    def test_empty_score_is_perfect(self) -> None:
        """Empty module has perfect score."""
        score = MutationScore(module="test")
        assert score.score == 1.0


class TestMutationReport:
    """Property tests for MutationReport."""

    @given(
        mutants=st.lists(
            st.tuples(file_paths, line_numbers, mutant_statuses),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_add_mutant_updates_modules(
        self, mutants: list[tuple[str, int, MutantStatus]]
    ) -> None:
        """Adding mutants updates module scores."""
        report = MutationReport()
        for file, line, status in mutants:
            mutant = create_mutant(file, line, MutationOperator.AOR, "a", "b", status)
            report.add_mutant(mutant)
        assert report.total_mutants == len(mutants)

    @given(
        mutants=st.lists(
            st.tuples(file_paths, line_numbers, mutant_statuses),
            min_size=1,
            max_size=20,
        )
    )
    @settings(max_examples=100)
    def test_survived_mutants_filter(
        self, mutants: list[tuple[str, int, MutantStatus]]
    ) -> None:
        """survived_mutants returns only survived."""
        report = MutationReport()
        for file, line, status in mutants:
            mutant = create_mutant(file, line, MutationOperator.AOR, "a", "b", status)
            report.add_mutant(mutant)
        survived = report.survived_mutants
        assert all(m.is_survived for m in survived)
        expected_count = sum(1 for _, _, s in mutants if s == MutantStatus.SURVIVED)
        assert len(survived) == expected_count

    def test_to_json_valid(self) -> None:
        """to_json produces valid JSON."""
        report = MutationReport()
        mutant = create_mutant("test.py", 1, MutationOperator.AOR, "a", "b")
        report.add_mutant(mutant)
        json_str = report.to_json()
        import json
        parsed = json.loads(json_str)
        assert "total_score" in parsed
        assert "modules" in parsed


class TestMutationConfig:
    """Property tests for MutationConfig."""

    @given(
        timeout=st.floats(min_value=1.0, max_value=10.0),
        workers=st.integers(min_value=1, max_value=16),
        threshold=st.floats(min_value=0.0, max_value=1.0),
    )
    @settings(max_examples=100)
    def test_valid_config(
        self, timeout: float, workers: int, threshold: float
    ) -> None:
        """Valid config produces no errors."""
        config = MutationConfig(
            timeout_multiplier=timeout,
            max_workers=workers,
            min_score_threshold=threshold,
        )
        errors = config.validate()
        assert len(errors) == 0

    @given(timeout=st.floats(max_value=0.9))
    @settings(max_examples=50)
    def test_invalid_timeout(self, timeout: float) -> None:
        """Invalid timeout produces error."""
        config = MutationConfig(timeout_multiplier=timeout)
        errors = config.validate()
        assert any("timeout" in e for e in errors)

    @given(workers=st.integers(max_value=0))
    @settings(max_examples=50)
    def test_invalid_workers(self, workers: int) -> None:
        """Invalid workers produces error."""
        config = MutationConfig(max_workers=workers)
        errors = config.validate()
        assert any("workers" in e for e in errors)

    def test_empty_source_paths(self) -> None:
        """Empty source paths produces error."""
        config = MutationConfig(source_paths=[])
        errors = config.validate()
        assert any("source_paths" in e for e in errors)


class TestMutantIdGeneration:
    """Property tests for mutant ID generation."""

    @given(
        file=file_paths,
        line=line_numbers,
        operator=st.text(min_size=1, max_size=20),
        replacement=code_snippets,
    )
    @settings(max_examples=100)
    def test_id_deterministic(
        self, file: str, line: int, operator: str, replacement: str
    ) -> None:
        """Same inputs produce same ID."""
        id1 = generate_mutant_id(file, line, operator, replacement)
        id2 = generate_mutant_id(file, line, operator, replacement)
        assert id1 == id2

    @given(
        file=file_paths,
        line1=line_numbers,
        line2=line_numbers,
        operator=st.text(min_size=1, max_size=20),
        replacement=code_snippets,
    )
    @settings(max_examples=100)
    def test_different_lines_different_ids(
        self, file: str, line1: int, line2: int, operator: str, replacement: str
    ) -> None:
        """Different lines produce different IDs."""
        if line1 != line2:
            id1 = generate_mutant_id(file, line1, operator, replacement)
            id2 = generate_mutant_id(file, line2, operator, replacement)
            assert id1 != id2

    @given(file=file_paths, line=line_numbers)
    @settings(max_examples=100)
    def test_id_length(self, file: str, line: int) -> None:
        """ID has consistent length."""
        mutant_id = generate_mutant_id(file, line, "op", "rep")
        assert len(mutant_id) == 12


class TestMutmutCommand:
    """Property tests for mutmut command generation."""

    @given(
        sources=st.lists(file_paths, min_size=1, max_size=3),
        tests=st.lists(file_paths, min_size=1, max_size=3),
        workers=st.integers(min_value=1, max_value=8),
    )
    @settings(max_examples=100)
    def test_command_contains_paths(
        self, sources: list[str], tests: list[str], workers: int
    ) -> None:
        """Command contains source and test paths."""
        config = MutationConfig(
            source_paths=sources,
            test_paths=tests,
            max_workers=workers,
            parallel=True,
        )
        cmd = get_mutmut_command(config)
        assert "mutmut" in cmd
        assert "run" in cmd
        for source in sources:
            assert source in cmd

    @given(parallel=st.booleans())
    @settings(max_examples=100)
    def test_parallel_flag(self, parallel: bool) -> None:
        """Parallel config affects command."""
        config = MutationConfig(parallel=parallel)
        cmd = get_mutmut_command(config)
        if parallel:
            assert "--runner" in cmd
        else:
            assert "--runner" not in cmd


class TestMutationTestRunner:
    """Property tests for MutationTestRunner."""

    @given(threshold=st.floats(min_value=0.0, max_value=1.0))
    @settings(max_examples=100)
    def test_check_threshold(self, threshold: float) -> None:
        """Threshold check works correctly."""
        config = MutationConfig(min_score_threshold=threshold)
        runner = MutationTestRunner(config)
        
        # Create report with known score
        report = MutationReport()
        # Add 10 killed, 0 survived = 100% score
        for i in range(10):
            mutant = create_mutant(
                "test.py", i, MutationOperator.AOR, "a", "b", MutantStatus.KILLED
            )
            report.add_mutant(mutant)
        
        # 100% score should always meet threshold
        assert runner.check_threshold(report) is True

    def test_validate_config(self) -> None:
        """Runner validates config."""
        config = MutationConfig()
        runner = MutationTestRunner(config)
        errors = runner.validate_config()
        assert len(errors) == 0

    def test_generate_report_summary(self) -> None:
        """Summary generation works."""
        config = MutationConfig()
        runner = MutationTestRunner(config)
        report = MutationReport()
        mutant = create_mutant("test.py", 1, MutationOperator.AOR, "a", "b")
        report.add_mutant(mutant)
        summary = runner.generate_report_summary(report)
        assert "Mutation Testing Report" in summary
        assert "Total Score" in summary


class TestMutationScoreInvariants:
    """Invariant tests for mutation scores."""

    @given(killed=positive_ints, survived=positive_ints, skipped=positive_ints)
    @settings(max_examples=100)
    def test_score_bounds(
        self, killed: int, survived: int, skipped: int
    ) -> None:
        """Score is always between 0 and 1."""
        score = MutationScore(
            module="test",
            total_mutants=killed + survived + skipped,
            killed=killed,
            survived=survived,
            skipped=skipped,
        )
        assert 0.0 <= score.score <= 1.0

    @given(
        mutants=st.lists(
            st.tuples(file_paths, mutant_statuses),
            min_size=1,
            max_size=50,
        )
    )
    @settings(max_examples=100)
    def test_report_score_bounds(
        self, mutants: list[tuple[str, MutantStatus]]
    ) -> None:
        """Report score is always between 0 and 1."""
        report = MutationReport()
        for i, (file, status) in enumerate(mutants):
            mutant = create_mutant(file, i, MutationOperator.AOR, "a", "b", status)
            report.add_mutant(mutant)
        assert 0.0 <= report.total_score <= 1.0
