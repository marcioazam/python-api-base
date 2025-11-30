"""response_transformation enums.

**Feature: shared-modules-code-review-fixes, Task 9.1**
**Validates: Requirements 3.3**
"""

from enum import Enum


class TransformationType(Enum):
    """Types of transformations."""

    FIELD_RENAME = "field_rename"
    FIELD_REMOVE = "field_remove"
    FIELD_ADD = "field_add"
    FIELD_TRANSFORM = "field_transform"
    STRUCTURE_CHANGE = "structure_change"
    FORMAT_CHANGE = "format_change"
