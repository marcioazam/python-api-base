"""Property-based tests for Runbook Generation.

**Feature: api-architecture-analysis, Property: Runbook operations**
**Validates: Requirements 18.4**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime

from my_api.shared.runbook import (
    Runbook,
    RunbookType,
    Severity,
    Step,
    RunbookGenerator,
)


@st.composite
def step_strategy(draw: st.DrawFn) -> Step:
    """Generate valid runbook step."""
    return Step(
        order=draw(st.integers(min_value=1, max_value=100)),
        title=draw(st.text(min_size=1, max_size=50)),
        description=draw(st.text(min_size=1, max_size=200)),
        commands=draw(st.lists(st.text(min_size=1, max_size=50), max_size=5)),
        timeout_minutes=draw(st.integers(min_value=1, max_value=60))
    )


@st.composite
def runbook_strategy(draw: st.DrawFn) -> Runbook:
    """Generate valid runbook."""
    return Runbook(
        id=draw(st.text(alphabet="abcdefghijklmnopqrstuvwxyz0123456789", min_size=5, max_size=20)),
        title=draw(st.text(min_size=1, max_size=100)),
        description=draw(st.text(min_size=1, max_size=500)),
        runbook_type=draw(st.sampled_from(list(RunbookType))),
        severity=draw(st.sampled_from(list(Severity) + [None])),
        steps=draw(st.lists(step_strategy(), min_size=0, max_size=5))
    )


class TestRunbookGeneratorProperties:
    """Property tests for runbook generator."""

    @given(runbook_strategy())
    @settings(max_examples=50)
    def test_markdown_contains_title(self, runbook: Runbook) -> None:
        """Generated markdown contains runbook title."""
        generator = RunbookGenerator()
        markdown = generator.generate_markdown(runbook)
        assert runbook.title in markdown

    @given(runbook_strategy())
    @settings(max_examples=50)
    def test_markdown_contains_description(self, runbook: Runbook) -> None:
        """Generated markdown contains description."""
        generator = RunbookGenerator()
        markdown = generator.generate_markdown(runbook)
        assert runbook.description in markdown

    @given(runbook_strategy())
    @settings(max_examples=50)
    def test_markdown_contains_type(self, runbook: Runbook) -> None:
        """Generated markdown contains runbook type."""
        generator = RunbookGenerator()
        markdown = generator.generate_markdown(runbook)
        assert runbook.runbook_type.value in markdown

    @given(runbook_strategy())
    @settings(max_examples=50)
    def test_markdown_contains_all_steps(self, runbook: Runbook) -> None:
        """Generated markdown contains all step titles."""
        generator = RunbookGenerator()
        markdown = generator.generate_markdown(runbook)

        for step in runbook.steps:
            assert step.title in markdown

    @given(st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=5))
    @settings(max_examples=50)
    def test_markdown_contains_commands(self, commands: list[str]) -> None:
        """Generated markdown contains commands in code blocks."""
        step = Step(order=1, title="Test", description="Test step", commands=commands)
        runbook = Runbook(
            id="test",
            title="Test Runbook",
            description="Test",
            runbook_type=RunbookType.INCIDENT,
            steps=[step]
        )
        generator = RunbookGenerator()
        markdown = generator.generate_markdown(runbook)

        assert "```bash" in markdown
        for cmd in commands:
            assert cmd in markdown

    @given(st.lists(st.text(min_size=1, max_size=30), min_size=1, max_size=5))
    @settings(max_examples=50)
    def test_markdown_contains_prerequisites(self, prereqs: list[str]) -> None:
        """Generated markdown contains prerequisites."""
        runbook = Runbook(
            id="test",
            title="Test Runbook",
            description="Test",
            runbook_type=RunbookType.MAINTENANCE,
            prerequisites=prereqs
        )
        generator = RunbookGenerator()
        markdown = generator.generate_markdown(runbook)

        assert "Prerequisites" in markdown
        for prereq in prereqs:
            assert prereq in markdown

    @given(runbook_strategy())
    @settings(max_examples=50)
    def test_template_registration(self, runbook: Runbook) -> None:
        """Templates can be registered and retrieved."""
        generator = RunbookGenerator()
        generator.register_template(runbook)
        assert runbook.id in generator._templates
