"""Enterprise examples router - Re-export module.

**Feature: enterprise-generics-2025**
**Refactored: 2025 - Split 576 lines into focused modules in enterprise/**

This module re-exports the enterprise router for backward compatibility.
"""

from interface.v1.enterprise import router

__all__ = ["router"]
