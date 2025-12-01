"""Serialization utilities.

**Feature: architecture-restructuring-2025**
**Validates: Requirements 13.3**
"""

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID


class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for common Python types."""
    
    def default(self, obj: Any) -> Any:
        """Encode object to JSON-serializable format."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, date):
            return obj.isoformat()
        if isinstance(obj, UUID):
            return str(obj)
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, bytes):
            return obj.decode("utf-8", errors="replace")
        if is_dataclass(obj) and not isinstance(obj, type):
            return asdict(obj)
        if hasattr(obj, "model_dump"):
            return obj.model_dump()
        if hasattr(obj, "to_dict"):
            return obj.to_dict()
        return super().default(obj)


def to_json(obj: Any, **kwargs: Any) -> str:
    """Serialize object to JSON string.
    
    Args:
        obj: Object to serialize.
        **kwargs: Additional arguments for json.dumps.
        
    Returns:
        JSON string.
    """
    return json.dumps(obj, cls=JSONEncoder, **kwargs)


def from_json(data: str) -> Any:
    """Deserialize JSON string to object.
    
    Args:
        data: JSON string.
        
    Returns:
        Deserialized object.
    """
    return json.loads(data)
