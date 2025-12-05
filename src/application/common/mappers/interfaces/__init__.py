"""Mapper interfaces and protocols.

Provides abstract base classes and protocols for mappers.

**Feature: architecture-restructuring-2025**
"""

from application.common.mappers.interfaces.mapper_interface import IMapper
from application.common.mappers.interfaces.mapper_protocol import Mapper

__all__ = [
    "IMapper",
    "Mapper",
]
