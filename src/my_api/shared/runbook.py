"""Runbook Generation for incident response and troubleshooting."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """Incident severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class RunbookType(Enum):
    """Types of runbooks."""
    INCIDENT = "incident"
    TROUBLESHOOTING = "troubleshooting"
    MAINTENANCE = "maintenance"
    DEPLOYMENT = "deployment"


@dataclass
class Step:
    """Runbook step."""
    order: int
    title: str
    description: str
    commands: list[str] = field(default_factory=list)
    expected_output: str = ""
    rollback_commands: list[str] = field(default_factory=list)
    timeout_minutes: int = 5
    requires_approval: bool = False


@dataclass
class Runbook:
    """Runbook definition."""
    id: str
    title: str
    description: str
    runbook_type: RunbookType
    severity: Severity | None = None
    tags: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    prerequisites: list[str] = field(default_factory=list)
    contacts: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    version: str = "1.0.0"


class RunbookGenerator:
    """Generate runbooks from templates."""

    def __init__(self) -> None:
        self._templates: dict[str, Runbook] = {}

    def register_template(self, template: Runbook) -> None:
        """Register a runbook template."""
        self._templates[template.id] = template

    def generate_markdown(self, runbook: Runbook) -> str:
        """Generate markdown documentation."""
        lines = [
            f"# {runbook.title}",
            "",
            f"**Type:** {runbook.runbook_type.value}",
            f"**Version:** {runbook.version}",
        ]

        if runbook.severity:
            lines.append(f"**Severity:** {runbook.severity.value}")

        if runbook.tags:
            lines.append(f"**Tags:** {', '.join(runbook.tags)}")

        lines.extend(["", "## Description", "", runbook.description, ""])

        if runbook.prerequisites:
            lines.extend(["## Prerequisites", ""])
            for prereq in runbook.prerequisites:
                lines.append(f"- {prereq}")
            lines.append("")

        if runbook.contacts:
            lines.extend(["## Contacts", ""])
            for contact in runbook.contacts:
                lines.append(f"- {contact}")
            lines.append("")

        lines.extend(["## Steps", ""])
        for step in runbook.steps:
            lines.append(f"### Step {step.order}: {step.title}")
            lines.append("")
            lines.append(step.description)
            lines.append("")

            if step.commands:
                lines.append("**Commands:**")
                lines.append("```bash")
                lines.extend(step.commands)
                lines.append("```")
                lines.append("")

            if step.expected_output:
                lines.append(f"**Expected Output:** {step.expected_output}")
                lines.append("")

            if step.rollback_commands:
                lines.append("**Rollback:**")
                lines.append("```bash")
                lines.extend(step.rollback_commands)
                lines.append("```")
                lines.append("")

        return "\n".join(lines)
