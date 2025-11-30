"""WAF default security patterns for threat detection.

**Feature: file-size-compliance-phase2, Task 2.1**
**Validates: Requirements 1.1, 5.1, 5.2, 5.3**
"""

# Default SQL Injection patterns
# Note: Using bounded quantifiers (.{0,100}) to prevent ReDoS attacks
# **Feature: shared-modules-code-review-fixes, Task 5.1**
# **Validates: Requirements 5.1, 5.2**
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER)\b.{0,100}\b(FROM|INTO|SET|TABLE)\b)",
    r"(\bOR\b\s+\d+\s*=\s*\d+)",
    r"(\bAND\b\s+\d+\s*=\s*\d+)",
    r"(--\s*$|;\s*--)",
    r"(\b(EXEC|EXECUTE)\s*\()",
    r"(\/\*.{0,100}\*\/)",
    r"(\bWAITFOR\b\s+\bDELAY\b)",
    r"(\bBENCHMARK\b\s*\()",
    r"(\bSLEEP\b\s*\()",
    r"('.{0,100}\bOR\b.{0,100}')",
]

# Default XSS patterns
XSS_PATTERNS = [
    r"(<script[^>]*>.*?</script>)",
    r"(javascript\s*:)",
    r"(on\w+\s*=)",
    r"(<iframe[^>]*>)",
    r"(<object[^>]*>)",
    r"(<embed[^>]*>)",
    r"(<svg[^>]*onload)",
    r"(expression\s*\()",
    r"(vbscript\s*:)",
    r"(<img[^>]+onerror)",
]

# Default Path Traversal patterns
PATH_TRAVERSAL_PATTERNS = [
    r"(\.\.\/)",
    r"(\.\.\\)",
    r"(%2e%2e%2f)",
    r"(%2e%2e\/)",
    r"(\.\.%2f)",
    r"(%2e%2e%5c)",
    r"(\/etc\/passwd)",
    r"(\/etc\/shadow)",
    r"(c:\\windows)",
    r"(%00)",
]

# Default Command Injection patterns
COMMAND_INJECTION_PATTERNS = [
    r"(;\s*\w+)",
    r"(\|\s*\w+)",
    r"(`[^`]+`)",
    r"(\$\([^)]+\))",
    r"(\b(cat|ls|dir|type|echo|wget|curl)\b)",
    r"(>\s*\/)",
    r"(<\s*\/)",
    r"(\b(rm|del|rmdir)\b\s+-)",
]
