"""AsyncAPI enums.

**Feature: code-review-refactoring, Task 18.4: Refactor asyncapi.py**
**Validates: Requirements 5.10**
"""

from enum import Enum


class ProtocolType(str, Enum):
    """Supported message broker protocols."""

    KAFKA = "kafka"
    AMQP = "amqp"
    MQTT = "mqtt"
    WS = "ws"
    HTTP = "http"
    REDIS = "redis"
    NATS = "nats"


class SecuritySchemeType(str, Enum):
    """Security scheme types."""

    USER_PASSWORD = "userPassword"
    API_KEY = "apiKey"
    X509 = "X509"
    SYMMETRIC_ENCRYPTION = "symmetricEncryption"
    ASYMMETRIC_ENCRYPTION = "asymmetricEncryption"
    HTTP_API_KEY = "httpApiKey"
    HTTP = "http"
    OAUTH2 = "oauth2"
    OPENID_CONNECT = "openIdConnect"
    PLAIN = "plain"
    SCRAM_SHA256 = "scramSha256"
    SCRAM_SHA512 = "scramSha512"
    GSSAPI = "gssapi"
