"""Mapper implementations and interfaces.

Organized into subpackages by responsibility:
- interfaces/: Mapper interfaces and protocols (IMapper, Mapper)
- implementations/: Concrete mapper implementations (AutoMapper, GenericMapper)
- errors/: Mapper-specific exceptions (MapperError)

**Feature: architecture-restructuring-2025**
"""

from application.common.mappers.errors import MapperError
from application.common.mappers.implementations import (
    AutoMapper,
    GenericMapper,
)
from application.common.mappers.interfaces import (
    IMapper,
    Mapper,
)

__all__ = [
    "AutoMapper",
    "GenericMapper",
    "IMapper",
    "Mapper",
    "MapperError",
]
