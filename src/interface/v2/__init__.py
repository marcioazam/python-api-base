"""API v2 module with versioned endpoints.

Version 2 of the API with enhanced features and breaking changes from v1.

**Feature: interface-modules-workflow-analysis**
**Validates: Requirements 1.1, 1.2, 1.3**
"""

from interface.v2.examples_router import router as examples_v2_router

__all__ = ["examples_v2_router"]
