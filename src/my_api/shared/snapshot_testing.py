"""API Snapshot Testing Module.

Provides utilities for snapshot testing of API responses,
including schema comparison and breaking change detection.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any
import json
import hashlib


class ChangeType(Enum):
    """Type of schema change."""
    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    TYPE_CHANGED = "type_changed"


class ChangeSeverity(Enum):
    """Severity of a schema change."""
    COMPATIBLE = "compatible"
    BREAKING = "breaking"
    UNKNOWN = "unknown"


@dataclass(frozen=True, slots=True)
class SchemaChange:
    """Represents a change in API schema."""
    path: str
    change_type: ChangeType
    severity: ChangeSeverity
    old_value: Any = None
    new_value: Any = None
    message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "change_type": self.change_type.value,
                "severity": self.severity.value, "old_value": str(self.old_value),
                "new_value": str(self.new_value), "message": self.message}


@dataclass
class Snapshot:
    """API response snapshot."""
    name: str
    schema: dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    version: str = "1.0.0"
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def hash(self) -> str:
        content = json.dumps(self.schema, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "schema": self.schema, "hash": self.hash,
                "timestamp": self.timestamp.isoformat(), "version": self.version,
                "metadata": self.metadata}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Snapshot":
        return cls(name=data["name"], schema=data["schema"], version=data.get("version", "1.0.0"),
                   timestamp=datetime.fromisoformat(data["timestamp"]),
                   metadata=data.get("metadata", {}))

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ComparisonResult:
    """Result of comparing two snapshots."""
    snapshot_name: str
    changes: list[SchemaChange] = field(default_factory=list)
    is_compatible: bool = True

    @property
    def has_breaking_changes(self) -> bool:
        return any(c.severity == ChangeSeverity.BREAKING for c in self.changes)

    @property
    def breaking_changes(self) -> list[SchemaChange]:
        return [c for c in self.changes if c.severity == ChangeSeverity.BREAKING]

    @property
    def compatible_changes(self) -> list[SchemaChange]:
        return [c for c in self.changes if c.severity == ChangeSeverity.COMPATIBLE]

    def to_dict(self) -> dict[str, Any]:
        return {"snapshot_name": self.snapshot_name, "is_compatible": self.is_compatible,
                "has_breaking_changes": self.has_breaking_changes,
                "changes": [c.to_dict() for c in self.changes]}


class SnapshotStore:
    """Stores and retrieves snapshots."""
    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir
        self._storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, name: str) -> Path:
        safe_name = name.replace("/", "_").replace("\\", "_")
        return self._storage_dir / f"{safe_name}.json"

    def save(self, snapshot: Snapshot) -> None:
        path = self._get_path(snapshot.name)
        path.write_text(snapshot.to_json())

    def load(self, name: str) -> Snapshot | None:
        path = self._get_path(name)
        if not path.exists():
            return None
        try:
            data = json.loads(path.read_text())
            return Snapshot.from_dict(data)
        except (json.JSONDecodeError, KeyError):
            return None

    def exists(self, name: str) -> bool:
        return self._get_path(name).exists()

    def delete(self, name: str) -> bool:
        path = self._get_path(name)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_all(self) -> list[str]:
        return [p.stem for p in self._storage_dir.glob("*.json")]


class SchemaComparator:
    """Compares two schemas and detects changes."""
    def __init__(self) -> None:
        self._breaking_removals = True
        self._breaking_type_changes = True

    def compare(self, old: dict[str, Any], new: dict[str, Any], path: str = "") -> list[SchemaChange]:
        changes: list[SchemaChange] = []
        old_keys = set(old.keys()) if isinstance(old, dict) else set()
        new_keys = set(new.keys()) if isinstance(new, dict) else set()

        for key in old_keys - new_keys:
            full_path = f"{path}.{key}" if path else key
            changes.append(SchemaChange(path=full_path, change_type=ChangeType.REMOVED,
                severity=ChangeSeverity.BREAKING if self._breaking_removals else ChangeSeverity.COMPATIBLE,
                old_value=old[key], message=f"Field '{key}' was removed"))

        for key in new_keys - old_keys:
            full_path = f"{path}.{key}" if path else key
            changes.append(SchemaChange(path=full_path, change_type=ChangeType.ADDED,
                severity=ChangeSeverity.COMPATIBLE, new_value=new[key],
                message=f"Field '{key}' was added"))

        for key in old_keys & new_keys:
            full_path = f"{path}.{key}" if path else key
            old_val, new_val = old[key], new[key]

            if type(old_val) != type(new_val):
                changes.append(SchemaChange(path=full_path, change_type=ChangeType.TYPE_CHANGED,
                    severity=ChangeSeverity.BREAKING if self._breaking_type_changes else ChangeSeverity.COMPATIBLE,
                    old_value=type(old_val).__name__, new_value=type(new_val).__name__,
                    message=f"Type changed from {type(old_val).__name__} to {type(new_val).__name__}"))
            elif isinstance(old_val, dict) and isinstance(new_val, dict):
                changes.extend(self.compare(old_val, new_val, full_path))
            elif isinstance(old_val, list) and isinstance(new_val, list):
                if old_val and new_val and isinstance(old_val[0], dict) and isinstance(new_val[0], dict):
                    changes.extend(self.compare(old_val[0], new_val[0], f"{full_path}[]"))
            elif old_val != new_val:
                changes.append(SchemaChange(path=full_path, change_type=ChangeType.MODIFIED,
                    severity=ChangeSeverity.COMPATIBLE, old_value=old_val, new_value=new_val,
                    message=f"Value changed"))
        return changes


class SnapshotTester:
    """Main snapshot testing class."""
    def __init__(self, storage_dir: Path) -> None:
        self._store = SnapshotStore(storage_dir)
        self._comparator = SchemaComparator()

    def create_snapshot(self, name: str, schema: dict[str, Any], version: str = "1.0.0") -> Snapshot:
        snapshot = Snapshot(name=name, schema=schema, version=version)
        self._store.save(snapshot)
        return snapshot

    def update_snapshot(self, name: str, schema: dict[str, Any], version: str = "1.0.0") -> Snapshot:
        return self.create_snapshot(name, schema, version)

    def get_snapshot(self, name: str) -> Snapshot | None:
        return self._store.load(name)

    def compare_with_snapshot(self, name: str, current_schema: dict[str, Any]) -> ComparisonResult:
        stored = self._store.load(name)
        if stored is None:
            return ComparisonResult(snapshot_name=name, changes=[], is_compatible=True)
        changes = self._comparator.compare(stored.schema, current_schema)
        is_compatible = not any(c.severity == ChangeSeverity.BREAKING for c in changes)
        return ComparisonResult(snapshot_name=name, changes=changes, is_compatible=is_compatible)

    def assert_matches(self, name: str, current_schema: dict[str, Any], update_on_mismatch: bool = False) -> bool:
        result = self.compare_with_snapshot(name, current_schema)
        if result.has_breaking_changes:
            if update_on_mismatch:
                self.update_snapshot(name, current_schema)
            return False
        return True

    def list_snapshots(self) -> list[str]:
        return self._store.list_all()

    def delete_snapshot(self, name: str) -> bool:
        return self._store.delete(name)


def extract_schema_from_response(response: dict[str, Any]) -> dict[str, Any]:
    """Extract schema structure from a response."""
    def get_type_schema(value: Any) -> dict[str, Any]:
        if value is None:
            return {"type": "null"}
        if isinstance(value, bool):
            return {"type": "boolean"}
        if isinstance(value, int):
            return {"type": "integer"}
        if isinstance(value, float):
            return {"type": "number"}
        if isinstance(value, str):
            return {"type": "string"}
        if isinstance(value, list):
            if not value:
                return {"type": "array", "items": {}}
            return {"type": "array", "items": get_type_schema(value[0])}
        if isinstance(value, dict):
            return {"type": "object", "properties": {k: get_type_schema(v) for k, v in value.items()}}
        return {"type": "unknown"}
    return get_type_schema(response)
