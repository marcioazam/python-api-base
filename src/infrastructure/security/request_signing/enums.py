"""request_signing enums.

**Feature: shared-modules-code-review-fixes, Task 8.1**
**Validates: Requirements 3.1**
"""

from enum import Enum


class HashAlgorithm(str, Enum):
    """Supported hash algorithms for HMAC."""

    SHA256 = "sha256"
    SHA384 = "sha384"
    SHA512 = "sha512"
