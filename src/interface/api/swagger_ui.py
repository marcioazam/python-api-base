"""Interactive API Documentation with Swagger UI customization."""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class AuthType(Enum):
    """Authentication types for try-it-out."""
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"
    OAUTH2 = "oauth2"


@dataclass
class SwaggerUIConfig:
    """Swagger UI configuration."""
    title: str = "API Documentation"
    version: str = "1.0.0"
    description: str = ""
    logo_url: str | None = None
    favicon_url: str | None = None
    theme: str = "default"
    deep_linking: bool = True
    display_request_duration: bool = True
    filter: bool = True
    show_extensions: bool = True
    show_common_extensions: bool = True
    try_it_out_enabled: bool = True
    persist_authorization: bool = True
    syntax_highlight_theme: str = "monokai"
    custom_css: str = ""
    custom_js: str = ""


@dataclass
class AuthConfig:
    """Authentication configuration for try-it-out."""
    auth_type: AuthType
    name: str
    description: str = ""
    scheme: str = "bearer"
    bearer_format: str = "JWT"
    api_key_location: str = "header"
    api_key_name: str = "X-API-Key"
    oauth2_flows: dict[str, Any] = field(default_factory=dict)


class SwaggerUIGenerator:
    """Generate customized Swagger UI HTML."""

    def __init__(self, config: SwaggerUIConfig) -> None:
        self._config = config
        self._auth_configs: list[AuthConfig] = []

    def add_auth(self, auth: AuthConfig) -> None:
        """Add authentication configuration."""
        self._auth_configs.append(auth)

    def generate_html(self, openapi_url: str = "/openapi.json") -> str:
        """Generate Swagger UI HTML."""
        return f'''<!DOCTYPE html>
<html>
<head>
    <title>{self._config.title}</title>
    <link rel="stylesheet" href="https://unpkg.com/swagger-ui-dist@5/swagger-ui.css">
    {self._generate_favicon()}
    <style>
        .swagger-ui .topbar {{ display: none; }}
        {self._config.custom_css}
    </style>
</head>
<body>
    <div id="swagger-ui"></div>
    <script src="https://unpkg.com/swagger-ui-dist@5/swagger-ui-bundle.js"></script>
    <script>
        window.onload = function() {{
            SwaggerUIBundle({{
                url: "{openapi_url}",
                dom_id: "#swagger-ui",
                deepLinking: {str(self._config.deep_linking).lower()},
                displayRequestDuration: {str(self._config.display_request_duration).lower()},
                filter: {str(self._config.filter).lower()},
                showExtensions: {str(self._config.show_extensions).lower()},
                showCommonExtensions: {str(self._config.show_common_extensions).lower()},
                tryItOutEnabled: {str(self._config.try_it_out_enabled).lower()},
                persistAuthorization: {str(self._config.persist_authorization).lower()},
                syntaxHighlight: {{ theme: "{self._config.syntax_highlight_theme}" }}
            }});
        }};
        {self._config.custom_js}
    </script>
</body>
</html>'''

    def _generate_favicon(self) -> str:
        if self._config.favicon_url:
            return f'<link rel="icon" href="{self._config.favicon_url}">'
        return ""

    def generate_security_schemes(self) -> dict[str, Any]:
        """Generate OpenAPI security schemes."""
        schemes: dict[str, Any] = {}
        for auth in self._auth_configs:
            if auth.auth_type == AuthType.BEARER:
                schemes[auth.name] = {
                    "type": "http",
                    "scheme": auth.scheme,
                    "bearerFormat": auth.bearer_format,
                    "description": auth.description
                }
            elif auth.auth_type == AuthType.API_KEY:
                schemes[auth.name] = {
                    "type": "apiKey",
                    "in": auth.api_key_location,
                    "name": auth.api_key_name,
                    "description": auth.description
                }
            elif auth.auth_type == AuthType.BASIC:
                schemes[auth.name] = {
                    "type": "http",
                    "scheme": "basic",
                    "description": auth.description
                }
            elif auth.auth_type == AuthType.OAUTH2:
                schemes[auth.name] = {
                    "type": "oauth2",
                    "flows": auth.oauth2_flows,
                    "description": auth.description
                }
        return schemes
