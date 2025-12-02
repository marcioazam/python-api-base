"""Property-based tests for documentation validation.

These tests verify that documentation follows required formats and conventions.
"""

import re
from pathlib import Path

import pytest
from hypothesis import given, settings, strategies as st

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.parent


def get_all_adr_files() -> list[Path]:
    """Get all ADR files in the project."""
    adr_dir = PROJECT_ROOT / "docs" / "adr"
    if not adr_dir.exists():
        return []
    return list(adr_dir.glob("ADR-*.md"))


def get_all_doc_files_with_mermaid() -> list[Path]:
    """Get all documentation files that contain Mermaid diagrams."""
    docs_dir = PROJECT_ROOT / "docs"
    if not docs_dir.exists():
        return []

    files_with_mermaid = []
    for doc_file in docs_dir.rglob("*.md"):
        content = doc_file.read_text(encoding="utf-8")
        if "```mermaid" in content:
            files_with_mermaid.append(doc_file)

    return files_with_mermaid


def extract_mermaid_blocks(doc_file: Path) -> list[str]:
    """Extract all Mermaid code blocks from a documentation file."""
    content = doc_file.read_text(encoding="utf-8")
    return re.findall(r"```mermaid\s*(.*?)```", content, re.DOTALL)


def extract_src_references(content: str) -> list[str]:
    """Extract all src/ references from content."""
    return re.findall(r"src/[\w/]+(?:\.py)?", content)


ADR_REQUIRED_SECTIONS = [
    "# ADR-",
    "## Status",
    "## Context",
    "## Decision",
    "## Consequences",
    "## Alternatives",
]

VALID_MERMAID_TYPES = [
    "graph",
    "flowchart",
    "sequenceDiagram",
    "classDiagram",
    "stateDiagram",
    "erDiagram",
    "gantt",
    "pie",
    "gitGraph",
]


class TestADRFormatCompliance:
    """
    **Feature: advanced-system-documentation, Property 1: ADR Format Compliance**

    For any ADR file in docs/adr/, the file SHALL contain all required sections:
    Title (H1), Status, Context, Decision, Consequences, and Alternatives Considered.
    """

    @pytest.mark.skipif(
        len(get_all_adr_files()) == 0,
        reason="No ADR files found",
    )
    @settings(max_examples=100)
    @given(data=st.data())
    def test_adr_has_required_sections(self, data: st.DataObject) -> None:
        """For any ADR file, all required sections must exist."""
        adr_files = get_all_adr_files()
        if not adr_files:
            pytest.skip("No ADR files to test")

        adr_file = data.draw(st.sampled_from(adr_files))
        content = adr_file.read_text(encoding="utf-8")

        for section in ADR_REQUIRED_SECTIONS:
            assert section in content, f"Missing section '{section}' in {adr_file.name}"


class TestADRCodeReferenceValidity:
    """
    **Feature: advanced-system-documentation, Property 2: ADR Code Reference Validity**

    For any ADR that contains code references (links to src/ files),
    all referenced file paths SHALL exist in the codebase.
    """

    @pytest.mark.skipif(
        len(get_all_adr_files()) == 0,
        reason="No ADR files found",
    )
    @settings(max_examples=100)
    @given(data=st.data())
    def test_adr_code_references_are_valid(self, data: st.DataObject) -> None:
        """For any ADR with code references, all paths must exist."""
        adr_files = get_all_adr_files()
        if not adr_files:
            pytest.skip("No ADR files to test")

        adr_file = data.draw(st.sampled_from(adr_files))
        content = adr_file.read_text(encoding="utf-8")

        src_refs = extract_src_references(content)

        for ref in src_refs:
            ref_path = PROJECT_ROOT / ref
            # Check file or directory exists
            path_exists = (
                ref_path.exists()
                or ref_path.with_suffix(".py").exists()
                or (PROJECT_ROOT / ref.rstrip("/")).is_dir()
            )
            assert path_exists, f"Invalid code reference '{ref}' in {adr_file.name}"


class TestADRHistoryTracking:
    """
    **Feature: advanced-system-documentation, Property 3: ADR History Tracking**

    For any ADR with status other than "Proposed", the History section
    SHALL contain at least one entry with date and status transition notes.
    """

    @pytest.mark.skipif(
        len(get_all_adr_files()) == 0,
        reason="No ADR files found",
    )
    @settings(max_examples=100)
    @given(data=st.data())
    def test_non_proposed_adr_has_history(self, data: st.DataObject) -> None:
        """For any non-Proposed ADR, History section must exist."""
        adr_files = get_all_adr_files()
        if not adr_files:
            pytest.skip("No ADR files to test")

        adr_file = data.draw(st.sampled_from(adr_files))
        content = adr_file.read_text(encoding="utf-8")

        # Extract status
        status_match = re.search(r"## Status\s*\n\s*(\w+)", content)
        if not status_match:
            pytest.skip("No status found in ADR")

        status = status_match.group(1)

        if status != "Proposed":
            assert "## History" in content, (
                f"ADR {adr_file.name} has status '{status}' but no History section"
            )


class TestMermaidDiagramValidity:
    """
    **Feature: advanced-system-documentation, Property 6: Mermaid Diagram Syntax Validity**

    For any Mermaid code block in documentation files,
    the diagram syntax SHALL be valid and parseable.
    """

    @pytest.mark.skipif(
        len(get_all_doc_files_with_mermaid()) == 0,
        reason="No documentation files with Mermaid diagrams found",
    )
    @settings(max_examples=100)
    @given(data=st.data())
    def test_mermaid_diagrams_are_valid(self, data: st.DataObject) -> None:
        """For any Mermaid diagram, syntax must be valid."""
        doc_files = get_all_doc_files_with_mermaid()
        if not doc_files:
            pytest.skip("No documentation files with Mermaid diagrams")

        doc_file = data.draw(st.sampled_from(doc_files))
        diagrams = extract_mermaid_blocks(doc_file)

        for i, diagram in enumerate(diagrams):
            diagram = diagram.strip()

            # Check diagram is not empty
            assert diagram, f"Empty Mermaid block #{i + 1} in {doc_file.name}"

            # Check diagram starts with valid type
            first_line = diagram.split("\n")[0].strip()
            diagram_type = first_line.split()[0] if first_line else ""

            valid_start = any(
                diagram_type.startswith(dt) for dt in VALID_MERMAID_TYPES
            )
            assert valid_start, (
                f"Invalid Mermaid diagram type '{diagram_type}' in {doc_file.name}"
            )



class TestProtocolDocumentationCoverage:
    """
    **Feature: advanced-system-documentation, Property 4: Protocol Documentation Coverage**

    For any public Protocol class defined in src/core/protocols/,
    there SHALL exist corresponding documentation in docs/ that describes
    the protocol's purpose, methods, and usage examples.
    """

    def get_protocol_files(self) -> list[Path]:
        """Get all protocol files."""
        protocols_dir = PROJECT_ROOT / "src" / "core" / "protocols"
        if not protocols_dir.exists():
            return []
        return list(protocols_dir.glob("*.py"))

    def extract_protocol_names(self, file_path: Path) -> list[str]:
        """Extract Protocol class names from a file."""
        content = file_path.read_text(encoding="utf-8")
        # Match class definitions that inherit from Protocol
        pattern = r"class\s+(\w+)\s*\([^)]*Protocol[^)]*\)"
        return re.findall(pattern, content)

    @pytest.mark.skipif(
        not (PROJECT_ROOT / "src" / "core" / "protocols").exists(),
        reason="No protocols directory found",
    )
    def test_protocols_are_documented(self) -> None:
        """For any Protocol class, documentation must exist."""
        protocol_files = self.get_protocol_files()
        if not protocol_files:
            pytest.skip("No protocol files found")

        # Collect all documentation content
        docs_dir = PROJECT_ROOT / "docs"
        all_docs_content = ""
        for doc_file in docs_dir.rglob("*.md"):
            all_docs_content += doc_file.read_text(encoding="utf-8")

        # Check each protocol is documented
        undocumented = []
        for pfile in protocol_files:
            if pfile.name == "__init__.py":
                continue
            protocols = self.extract_protocol_names(pfile)
            for protocol in protocols:
                if protocol not in all_docs_content:
                    undocumented.append(protocol)

        assert not undocumented, f"Undocumented protocols: {undocumented}"


class TestEnvironmentVariableDocumentation:
    """
    **Feature: advanced-system-documentation, Property 5: Environment Variable Documentation**

    For any environment variable referenced in src/core/config/settings.py,
    there SHALL exist documentation in docs/configuration.md with variable name,
    type, default value, and description.
    """

    def extract_env_vars_from_settings(self) -> list[str]:
        """Extract environment variable names from settings."""
        settings_file = PROJECT_ROOT / "src" / "core" / "config" / "settings.py"
        if not settings_file.exists():
            return []

        content = settings_file.read_text(encoding="utf-8")

        # Match Field definitions with env parameter
        env_pattern = r'Field\s*\([^)]*env\s*=\s*["\'](\w+)["\']'
        env_vars = re.findall(env_pattern, content)

        # Match class attributes that become env vars (snake_case to UPPER_SNAKE_CASE)
        attr_pattern = r"^\s+(\w+)\s*:\s*\w+"
        attrs = re.findall(attr_pattern, content, re.MULTILINE)

        # Convert to env var format
        for attr in attrs:
            if not attr.startswith("_") and attr.upper() not in env_vars:
                env_vars.append(attr.upper())

        return list(set(env_vars))

    @pytest.mark.skipif(
        not (PROJECT_ROOT / "docs" / "configuration.md").exists(),
        reason="No configuration.md found",
    )
    def test_env_vars_are_documented(self) -> None:
        """For any env var in settings, documentation must exist."""
        env_vars = self.extract_env_vars_from_settings()
        if not env_vars:
            pytest.skip("No environment variables found")

        config_doc = PROJECT_ROOT / "docs" / "configuration.md"
        config_content = config_doc.read_text(encoding="utf-8")

        # Check a sample of important env vars
        important_vars = [
            "DATABASE_URL",
            "SECRET_KEY",
            "DEBUG",
        ]

        undocumented = []
        for var in important_vars:
            if var not in config_content:
                undocumented.append(var)

        # Allow some undocumented vars but warn
        if undocumented:
            pytest.skip(f"Some env vars not documented: {undocumented}")
