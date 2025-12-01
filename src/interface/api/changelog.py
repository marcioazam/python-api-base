"""API Changelog Automation with breaking change detection."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
import re


class ChangeType(Enum):
    """Types of API changes."""
    ADDED = "added"
    CHANGED = "changed"
    DEPRECATED = "deprecated"
    REMOVED = "removed"
    FIXED = "fixed"
    SECURITY = "security"


class BreakingChangeType(Enum):
    """Types of breaking changes."""
    ENDPOINT_REMOVED = "endpoint_removed"
    FIELD_REMOVED = "field_removed"
    TYPE_CHANGED = "type_changed"
    REQUIRED_FIELD_ADDED = "required_field_added"
    RESPONSE_STRUCTURE_CHANGED = "response_structure_changed"


@dataclass
class Change:
    """Single changelog entry."""
    change_type: ChangeType
    description: str
    endpoint: str | None = None
    is_breaking: bool = False
    breaking_type: BreakingChangeType | None = None
    migration_guide: str | None = None


@dataclass
class Version:
    """Version with changes."""
    version: str
    date: datetime
    changes: list[Change] = field(default_factory=list)

    @property
    def has_breaking_changes(self) -> bool:
        return any(c.is_breaking for c in self.changes)


class SemanticVersion:
    """Semantic version parser and comparator."""

    def __init__(self, version: str) -> None:
        match = re.match(r"^(\d+)\.(\d+)\.(\d+)(?:-(.+))?$", version)
        if not match:
            raise ValueError(f"Invalid version: {version}")
        self.major = int(match.group(1))
        self.minor = int(match.group(2))
        self.patch = int(match.group(3))
        self.prerelease = match.group(4)

    def __str__(self) -> str:
        base = f"{self.major}.{self.minor}.{self.patch}"
        if self.prerelease:
            return f"{base}-{self.prerelease}"
        return base

    def bump_major(self) -> "SemanticVersion":
        return SemanticVersion(f"{self.major + 1}.0.0")

    def bump_minor(self) -> "SemanticVersion":
        return SemanticVersion(f"{self.major}.{self.minor + 1}.0")

    def bump_patch(self) -> "SemanticVersion":
        return SemanticVersion(f"{self.major}.{self.minor}.{self.patch + 1}")


class BreakingChangeDetector:
    """Detect breaking changes between API versions."""

    def detect(
        self,
        old_spec: dict[str, Any],
        new_spec: dict[str, Any]
    ) -> list[Change]:
        """Detect breaking changes between OpenAPI specs."""
        changes: list[Change] = []

        old_paths = old_spec.get("paths", {})
        new_paths = new_spec.get("paths", {})

        # Removed endpoints
        for path in old_paths:
            if path not in new_paths:
                changes.append(Change(
                    change_type=ChangeType.REMOVED,
                    description=f"Endpoint {path} was removed",
                    endpoint=path,
                    is_breaking=True,
                    breaking_type=BreakingChangeType.ENDPOINT_REMOVED
                ))

        # Check schema changes
        old_schemas = old_spec.get("components", {}).get("schemas", {})
        new_schemas = new_spec.get("components", {}).get("schemas", {})

        for name, old_schema in old_schemas.items():
            if name not in new_schemas:
                continue
            new_schema = new_schemas[name]
            schema_changes = self._compare_schemas(name, old_schema, new_schema)
            changes.extend(schema_changes)

        return changes

    def _compare_schemas(
        self,
        name: str,
        old_schema: dict[str, Any],
        new_schema: dict[str, Any]
    ) -> list[Change]:
        """Compare two schemas for breaking changes."""
        changes: list[Change] = []

        old_props = old_schema.get("properties", {})
        new_props = new_schema.get("properties", {})
        old_required = set(old_schema.get("required", []))
        new_required = set(new_schema.get("required", []))

        # Removed fields
        for prop in old_props:
            if prop not in new_props:
                changes.append(Change(
                    change_type=ChangeType.REMOVED,
                    description=f"Field {prop} removed from {name}",
                    is_breaking=True,
                    breaking_type=BreakingChangeType.FIELD_REMOVED
                ))

        # New required fields
        for prop in new_required - old_required:
            if prop in old_props:
                changes.append(Change(
                    change_type=ChangeType.CHANGED,
                    description=f"Field {prop} in {name} is now required",
                    is_breaking=True,
                    breaking_type=BreakingChangeType.REQUIRED_FIELD_ADDED
                ))

        return changes


class ChangelogGenerator:
    """Generate changelog documentation."""

    def __init__(self) -> None:
        self._versions: list[Version] = []

    def add_version(self, version: Version) -> None:
        """Add a version to the changelog."""
        self._versions.append(version)
        self._versions.sort(key=lambda v: v.date, reverse=True)

    def generate_markdown(self) -> str:
        """Generate markdown changelog."""
        lines = ["# Changelog", "", "All notable changes to this API.", ""]

        for version in self._versions:
            date_str = version.date.strftime("%Y-%m-%d")
            breaking = " ⚠️ BREAKING" if version.has_breaking_changes else ""
            lines.append(f"## [{version.version}] - {date_str}{breaking}")
            lines.append("")

            by_type: dict[ChangeType, list[Change]] = {}
            for change in version.changes:
                by_type.setdefault(change.change_type, []).append(change)

            for change_type in ChangeType:
                if change_type not in by_type:
                    continue
                lines.append(f"### {change_type.value.capitalize()}")
                for change in by_type[change_type]:
                    breaking_mark = " **BREAKING**" if change.is_breaking else ""
                    lines.append(f"- {change.description}{breaking_mark}")
                    if change.migration_guide:
                        lines.append(f"  - Migration: {change.migration_guide}")
                lines.append("")

        return "\n".join(lines)

    def suggest_version(
        self,
        current: str,
        changes: list[Change]
    ) -> str:
        """Suggest next version based on changes."""
        version = SemanticVersion(current)

        if any(c.is_breaking for c in changes):
            return str(version.bump_major())
        elif any(c.change_type == ChangeType.ADDED for c in changes):
            return str(version.bump_minor())
        else:
            return str(version.bump_patch())
