"""Property-based tests for Changelog Automation.

**Feature: api-architecture-analysis, Property: Changelog operations**
**Validates: Requirements 18.5**
"""

import pytest
from hypothesis import given, strategies as st, settings
from datetime import datetime

from my_api.shared.changelog import (
    Change,
    ChangeType,
    Version,
    SemanticVersion,
    BreakingChangeDetector,
    ChangelogGenerator,
)


class TestSemanticVersionProperties:
    """Property tests for semantic versioning."""

    @given(
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100)
    def test_version_round_trip(self, major: int, minor: int, patch: int) -> None:
        """Version string round trip."""
        version_str = f"{major}.{minor}.{patch}"
        version = SemanticVersion(version_str)
        assert str(version) == version_str

    @given(
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100)
    def test_bump_major_resets_minor_patch(
        self,
        major: int,
        minor: int,
        patch: int
    ) -> None:
        """Bumping major resets minor and patch."""
        version = SemanticVersion(f"{major}.{minor}.{patch}")
        bumped = version.bump_major()
        assert bumped.major == major + 1
        assert bumped.minor == 0
        assert bumped.patch == 0

    @given(
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100),
        st.integers(min_value=0, max_value=100)
    )
    @settings(max_examples=100)
    def test_bump_minor_resets_patch(
        self,
        major: int,
        minor: int,
        patch: int
    ) -> None:
        """Bumping minor resets patch."""
        version = SemanticVersion(f"{major}.{minor}.{patch}")
        bumped = version.bump_minor()
        assert bumped.major == major
        assert bumped.minor == minor + 1
        assert bumped.patch == 0


class TestChangelogGeneratorProperties:
    """Property tests for changelog generator."""

    @given(st.lists(st.sampled_from(list(ChangeType)), min_size=1, max_size=10))
    @settings(max_examples=50)
    def test_markdown_contains_all_change_types(
        self,
        change_types: list[ChangeType]
    ) -> None:
        """Generated markdown contains all change types."""
        generator = ChangelogGenerator()
        changes = [
            Change(change_type=ct, description=f"Test {ct.value}")
            for ct in change_types
        ]
        version = Version(
            version="1.0.0",
            date=datetime.utcnow(),
            changes=changes
        )
        generator.add_version(version)
        markdown = generator.generate_markdown()

        for ct in set(change_types):
            assert ct.value.capitalize() in markdown

    @given(st.booleans())
    @settings(max_examples=50)
    def test_breaking_changes_marked(self, is_breaking: bool) -> None:
        """Breaking changes are marked in output."""
        generator = ChangelogGenerator()
        change = Change(
            change_type=ChangeType.CHANGED,
            description="Test change",
            is_breaking=is_breaking
        )
        version = Version(
            version="1.0.0",
            date=datetime.utcnow(),
            changes=[change]
        )
        generator.add_version(version)
        markdown = generator.generate_markdown()

        if is_breaking:
            assert "BREAKING" in markdown
        else:
            assert "BREAKING" not in markdown or "⚠️ BREAKING" not in markdown

    def test_suggest_major_for_breaking(self) -> None:
        """Suggests major bump for breaking changes."""
        generator = ChangelogGenerator()
        changes = [Change(
            change_type=ChangeType.REMOVED,
            description="Removed endpoint",
            is_breaking=True
        )]
        suggested = generator.suggest_version("1.2.3", changes)
        assert suggested == "2.0.0"

    def test_suggest_minor_for_additions(self) -> None:
        """Suggests minor bump for additions."""
        generator = ChangelogGenerator()
        changes = [Change(
            change_type=ChangeType.ADDED,
            description="Added endpoint"
        )]
        suggested = generator.suggest_version("1.2.3", changes)
        assert suggested == "1.3.0"

    def test_suggest_patch_for_fixes(self) -> None:
        """Suggests patch bump for fixes."""
        generator = ChangelogGenerator()
        changes = [Change(
            change_type=ChangeType.FIXED,
            description="Fixed bug"
        )]
        suggested = generator.suggest_version("1.2.3", changes)
        assert suggested == "1.2.4"
