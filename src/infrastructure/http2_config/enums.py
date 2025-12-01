"""http2_config enums."""

from enum import Enum


class HTTPProtocol(Enum):
    """Supported HTTP protocols."""

    HTTP_1_1 = "http/1.1"
    HTTP_2 = "h2"
    HTTP_3 = "h3"

class PushPriority(Enum):
    """Server push priority levels."""

    HIGHEST = 0
    HIGH = 64
    NORMAL = 128
    LOW = 192
    LOWEST = 255
