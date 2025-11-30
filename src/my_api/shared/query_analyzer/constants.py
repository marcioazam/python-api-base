"""Query analyzer constants.

**Feature: shared-modules-phase3-fixes, Task 1.3**
**Validates: Requirements 2.1, 2.2, 2.4**
"""

import re

# Maximum query length to prevent ReDoS attacks
MAX_QUERY_LENGTH = 10000

# Pattern for valid SQL identifiers (table/column names)
ALLOWED_IDENTIFIER_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

# Timeout for regex operations (seconds)
REGEX_TIMEOUT_SECONDS = 1.0
