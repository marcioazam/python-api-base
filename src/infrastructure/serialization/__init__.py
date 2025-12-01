"""High-performance serialization utilities.

Provides orjson integration for fast JSON serialization.
"""

from src.infrastructure.serialization.orjson_config import (
    ORJSONResponse,
    PrettyORJSONResponse,
    ORJSONBaseModel,
    orjson_dumps,
    orjson_loads,
    default_serializer,
    configure_orjson,
    create_orjson_app,
    pydantic_orjson_dumps,
)

__all__ = [
    "ORJSONResponse",
    "PrettyORJSONResponse",
    "ORJSONBaseModel",
    "orjson_dumps",
    "orjson_loads",
    "default_serializer",
    "configure_orjson",
    "create_orjson_app",
    "pydantic_orjson_dumps",
]
