"""High-performance JSON serialization with orjson.

Configures FastAPI to use orjson for 10x faster JSON encoding/decoding.
Supports datetime, UUID, Decimal, and custom types.
"""

from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

import orjson
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel


def orjson_dumps(
    obj: Any,
    *,
    default: Any = None,
    option: int | None = None,
) -> bytes:
    """Serialize object to JSON bytes using orjson.

    Args:
        obj: Object to serialize.
        default: Default serializer for unknown types.
        option: orjson options (e.g., OPT_INDENT_2).

    Returns:
        JSON bytes.
    """
    opts = option or (
        orjson.OPT_SERIALIZE_NUMPY
        | orjson.OPT_SERIALIZE_UUID
        | orjson.OPT_UTC_Z
    )

    return orjson.dumps(obj, default=default, option=opts)


def orjson_loads(data: bytes | str) -> Any:
    """Deserialize JSON bytes/string using orjson.

    Args:
        data: JSON bytes or string.

    Returns:
        Deserialized object.
    """
    return orjson.loads(data)


def default_serializer(obj: Any) -> Any:
    """Default serializer for types not natively supported by orjson.

    Args:
        obj: Object to serialize.

    Returns:
        Serializable representation.

    Raises:
        TypeError: If object cannot be serialized.
    """
    if isinstance(obj, Decimal):
        return str(obj)
    if isinstance(obj, (datetime, date, time)):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    if isinstance(obj, set):
        return list(obj)
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if hasattr(obj, "__dict__"):
        return obj.__dict__

    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


class ORJSONResponse(JSONResponse):
    """FastAPI response class using orjson for serialization.

    10x faster than standard JSONResponse.

    Example:
        >>> @app.get("/users", response_class=ORJSONResponse)
        >>> async def get_users():
        ...     return {"users": [...]}
    """

    media_type = "application/json"

    def render(self, content: Any) -> bytes:
        """Render content to JSON bytes.

        Args:
            content: Content to serialize.

        Returns:
            JSON bytes.
        """
        return orjson_dumps(
            content,
            default=default_serializer,
            option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z,
        )


class PrettyORJSONResponse(ORJSONResponse):
    """ORJSONResponse with indented output for debugging."""

    def render(self, content: Any) -> bytes:
        """Render content to indented JSON bytes."""
        return orjson_dumps(
            content,
            default=default_serializer,
            option=(
                orjson.OPT_SERIALIZE_NUMPY
                | orjson.OPT_UTC_Z
                | orjson.OPT_INDENT_2
            ),
        )


def configure_orjson(app: FastAPI) -> None:
    """Configure FastAPI to use orjson for JSON serialization.

    Sets ORJSONResponse as the default response class.

    Args:
        app: FastAPI application instance.

    Example:
        >>> app = FastAPI()
        >>> configure_orjson(app)
    """
    app.default_response_class = ORJSONResponse


def create_orjson_app(
    title: str = "API",
    version: str = "1.0.0",
    **kwargs: Any,
) -> FastAPI:
    """Create FastAPI app with orjson configured.

    Args:
        title: API title.
        version: API version.
        **kwargs: Additional FastAPI arguments.

    Returns:
        FastAPI app with orjson response class.

    Example:
        >>> app = create_orjson_app(title="My API")
    """
    return FastAPI(
        title=title,
        version=version,
        default_response_class=ORJSONResponse,
        **kwargs,
    )


# Pydantic v2 integration
def pydantic_orjson_dumps(v: Any, *, default: Any = None) -> str:
    """Serialize for Pydantic model_dump_json.

    Args:
        v: Value to serialize.
        default: Default serializer.

    Returns:
        JSON string.
    """
    return orjson_dumps(v, default=default or default_serializer).decode()


class ORJSONBaseModel(BaseModel):
    """Pydantic BaseModel configured to use orjson.

    Example:
        >>> class User(ORJSONBaseModel):
        ...     name: str
        ...     created_at: datetime
        >>> 
        >>> user = User(name="John", created_at=datetime.now())
        >>> json_str = user.model_dump_json()  # Uses orjson
    """

    model_config = {
        "json_encoders": {
            datetime: lambda v: v.isoformat(),
            Decimal: str,
            UUID: str,
        },
    }

    def model_dump_json(self, **kwargs: Any) -> str:
        """Serialize model to JSON string using orjson."""
        return pydantic_orjson_dumps(self.model_dump(**kwargs))
