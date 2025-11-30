"""bff enums."""

from enum import Enum


class ClientType(Enum):
    """Supported client types."""

    WEB = "web"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    API = "api"
    UNKNOWN = "unknown"
