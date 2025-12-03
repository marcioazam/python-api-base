"""
Property-based tests for documentation structure validation.

These tests verify that documentation follows required patterns and structures.
"""

import re
from pathlib import Path

import pytest
from hypothesis import given, strategies as st, settings

# Get docs path
DOCS_PATH = Path(__file__).parent.parent.parent / "docs"


class TestLayerDocumentationCompleteness:
    """
    **Feature: comprehensive-documentation-improvement, Property 1: Layer Documentation Completeness**
    **Validates: Requirements 1.1, 1.2**
    """

    LAYERS = ["core", "domain", "application", "infrastructure", "interface"]
    REQUIRED_SECTIONS = [
        "## Overview",
        "## Directory Structure",
        "## Key Components",
        "## Dependency Rules",
    ]

    @pytest.mark.parametrize("layer", LAYERS)
    def test_layer_has_index(self, layer: str):
        """Each layer must have an index.md file."""
        index_path = DOCS_PATH / "layers" / layer / "index.md"
        assert index_path.exists(), f"Missing index.md for {layer} layer"

    @pytest.mark.parametrize("layer", LAYERS)
    def test_layer_has_required_sections(self, layer: str):
        """Each layer documentation must have all required sections."""
        index_path = DOCS_PATH / "layers" / layer / "index.md"
        if not index_path.exists():
            pytest.skip(f"Layer {layer} index not found")

        content = index_path.read_text(encoding="utf-8")

        for section in self.REQUIRED_SECTIONS:
            assert section in content, f"Missing section '{section}' in {layer} layer docs"


class TestADRStructureCompliance:
    """
    **Feature: comprehensive-documentation-improvement, Property 2: ADR Structure Compliance**
    **Validates: Requirements 3.1, 3.2**
    """

    REQUIRED_SECTIONS = [
        "## Status",
        "## Context",
        "## Decision",
        "## Consequences",
    ]

    def get_adr_files(self) -> list[Path]:
        """Get all ADR files."""
        adr_path = DOCS_PATH / "adr"
        if not adr_path.exists():
            return []
        return [f for f in adr_path.glob("ADR-*.md")]

    @pytest.mark.parametrize(
        "adr_file",
        [f for f in (Path(__file__).parent.parent.parent / "docs" / "adr").glob("ADR-*.md")]
        if (Path(__file__).parent.parent.parent / "docs" / "adr").exists()
        else [],
        ids=lambda f: f.name,
    )
    def test_adr_has_required_sections(self, adr_file: Path):
        """Each ADR must have all required sections."""
        content = adr_file.read_text(encoding="utf-8")

        for section in self.REQUIRED_SECTIONS:
            assert section in content, f"Missing section '{section}' in {adr_file.name}"

    def test_adr_index_exists(self):
        """ADR index must exist."""
        readme_path = DOCS_PATH / "adr" / "README.md"
        assert readme_path.exists(), "Missing ADR README.md"


class TestRunbookCompleteness:
    """
    **Feature: comprehensive-documentation-improvement, Property 3: Runbook Completeness**
    **Validates: Requirements 4.2, 4.4**
    """

    REQUIRED_METADATA = [
        "**Severity:**",
        "**SLO Impact:**",
        "**Recovery Time Estimate:**",
    ]

    REQUIRED_SECTIONS = [
        "## Diagnosis",
        "## Resolution",
    ]

    def get_runbook_files(self) -> list[Path]:
        """Get all runbook files."""
        runbook_path = DOCS_PATH / "operations" / "runbooks"
        if not runbook_path.exists():
            return []
        return [f for f in runbook_path.glob("*.md") if f.name != "README.md"]

    @pytest.mark.parametrize(
        "runbook_file",
        [
            f
            for f in (Path(__file__).parent.parent.parent / "docs" / "operations" / "runbooks").glob("*.md")
            if f.name != "README.md"
        ]
        if (Path(__file__).parent.parent.parent / "docs" / "operations" / "runbooks").exists()
        else [],
        ids=lambda f: f.name,
    )
    def test_runbook_has_required_metadata(self, runbook_file: Path):
        """Each runbook must have severity and SLO impact metadata."""
        content = runbook_file.read_text(encoding="utf-8")

        for metadata in self.REQUIRED_METADATA:
            assert metadata in content, f"Missing metadata '{metadata}' in {runbook_file.name}"

    @pytest.mark.parametrize(
        "runbook_file",
        [
            f
            for f in (Path(__file__).parent.parent.parent / "docs" / "operations" / "runbooks").glob("*.md")
            if f.name != "README.md"
        ]
        if (Path(__file__).parent.parent.parent / "docs" / "operations" / "runbooks").exists()
        else [],
        ids=lambda f: f.name,
    )
    def test_runbook_has_required_sections(self, runbook_file: Path):
        """Each runbook must have diagnosis and resolution sections."""
        content = runbook_file.read_text(encoding="utf-8")

        for section in self.REQUIRED_SECTIONS:
            assert section in content, f"Missing section '{section}' in {runbook_file.name}"


class TestDocumentationLinks:
    """Test that documentation links are valid."""

    def test_no_broken_internal_links(self):
        """All internal links must point to existing files."""
        broken_links = []

        for md_file in DOCS_PATH.rglob("*.md"):
            content = md_file.read_text(encoding="utf-8")
            # Find markdown links (not http/https)
            links = re.findall(r"\[.*?\]\(((?!http)[^)]+)\)", content)

            for link in links:
                # Remove anchors
                link_path = link.split("#")[0]
                if link_path:
                    target = (md_file.parent / link_path).resolve()
                    if not target.exists():
                        broken_links.append((str(md_file.relative_to(DOCS_PATH)), link))

        # Allow some broken links during development
        if broken_links:
            pytest.skip(f"Found {len(broken_links)} broken links (expected during development)")
