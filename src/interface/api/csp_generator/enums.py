"""CSP enums for directives and keywords.

**Feature: file-size-compliance-phase2, Task 2.4**
**Validates: Requirements 1.4, 5.1, 5.2, 5.3**
"""

from enum import Enum


class CSPDirective(str, Enum):
    """CSP directive names."""

    DEFAULT_SRC = "default-src"
    SCRIPT_SRC = "script-src"
    STYLE_SRC = "style-src"
    IMG_SRC = "img-src"
    FONT_SRC = "font-src"
    CONNECT_SRC = "connect-src"
    MEDIA_SRC = "media-src"
    OBJECT_SRC = "object-src"
    FRAME_SRC = "frame-src"
    FRAME_ANCESTORS = "frame-ancestors"
    BASE_URI = "base-uri"
    FORM_ACTION = "form-action"
    WORKER_SRC = "worker-src"
    MANIFEST_SRC = "manifest-src"
    REPORT_URI = "report-uri"
    REPORT_TO = "report-to"
    UPGRADE_INSECURE_REQUESTS = "upgrade-insecure-requests"
    BLOCK_ALL_MIXED_CONTENT = "block-all-mixed-content"


class CSPKeyword(str, Enum):
    """CSP source keywords."""

    SELF = "'self'"
    NONE = "'none'"
    UNSAFE_INLINE = "'unsafe-inline'"
    UNSAFE_EVAL = "'unsafe-eval'"
    STRICT_DYNAMIC = "'strict-dynamic'"
    UNSAFE_HASHES = "'unsafe-hashes'"
    WASM_UNSAFE_EVAL = "'wasm-unsafe-eval'"
