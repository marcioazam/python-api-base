"""Cache utility functions.

**Feature: code-review-refactoring, Task 17.2: Refactor caching.py**
**Validates: Requirements 5.5**
"""

import hashlib
from typing import Any
from collections.abc import Callable


def generate_cache_key(
    func: Callable[..., Any],
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> str:
    """Generate a cache key from function and arguments.

    Args:
        func: The function being cached.
        args: Positional arguments.
        kwargs: Keyword arguments.

    Returns:
        A unique cache key string.
    """
    key_parts = [func.__module__, func.__qualname__]

    for arg in args:
        try:
            key_parts.append(str(arg))
        except Exception:
            key_parts.append(str(id(arg)))

    for k, v in sorted(kwargs.items()):
        try:
            key_parts.append(f"{k}={v}")
        except Exception:
            key_parts.append(f"{k}={id(v)}")

    key_str = ":".join(key_parts)
    return hashlib.sha256(key_str.encode()).hexdigest()[:32]
