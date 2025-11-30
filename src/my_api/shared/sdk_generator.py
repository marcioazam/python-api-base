"""SDK Generation from OpenAPI specification."""

from dataclasses import dataclass
from typing import Any
from enum import Enum
import json


class SDKLanguage(Enum):
    """Supported SDK languages."""
    TYPESCRIPT = "typescript"
    PYTHON = "python"
    GO = "go"
    JAVA = "java"
    CSHARP = "csharp"


@dataclass
class SDKConfig:
    """SDK generation configuration."""
    language: SDKLanguage
    package_name: str
    version: str = "1.0.0"
    author: str = ""
    description: str = ""
    base_url: str = ""
    include_models: bool = True
    include_api_client: bool = True
    generate_tests: bool = False


@dataclass
class GeneratedFile:
    """Generated SDK file."""
    path: str
    content: str
    language: SDKLanguage


class SDKGenerator:
    """Generate SDK clients from OpenAPI spec."""

    def __init__(self, openapi_spec: dict[str, Any]) -> None:
        self._spec = openapi_spec
        self._info = openapi_spec.get("info", {})
        self._paths = openapi_spec.get("paths", {})
        self._schemas = openapi_spec.get("components", {}).get("schemas", {})

    def generate(self, config: SDKConfig) -> list[GeneratedFile]:
        """Generate SDK for specified language."""
        if config.language == SDKLanguage.TYPESCRIPT:
            return self._generate_typescript(config)
        elif config.language == SDKLanguage.PYTHON:
            return self._generate_python(config)
        elif config.language == SDKLanguage.GO:
            return self._generate_go(config)
        return []

    def _generate_typescript(self, config: SDKConfig) -> list[GeneratedFile]:
        """Generate TypeScript SDK."""
        files: list[GeneratedFile] = []

        # Package.json
        package_json = {
            "name": config.package_name,
            "version": config.version,
            "description": config.description,
            "main": "dist/index.js",
            "types": "dist/index.d.ts",
            "scripts": {"build": "tsc", "test": "jest"},
            "dependencies": {"axios": "^1.6.0"},
            "devDependencies": {"typescript": "^5.0.0", "@types/node": "^20.0.0"}
        }
        files.append(GeneratedFile(
            path="package.json",
            content=json.dumps(package_json, indent=2),
            language=SDKLanguage.TYPESCRIPT
        ))

        # Types
        types_content = self._generate_ts_types()
        files.append(GeneratedFile(
            path="src/types.ts",
            content=types_content,
            language=SDKLanguage.TYPESCRIPT
        ))

        # Client
        client_content = self._generate_ts_client(config)
        files.append(GeneratedFile(
            path="src/client.ts",
            content=client_content,
            language=SDKLanguage.TYPESCRIPT
        ))

        return files

    def _generate_ts_types(self) -> str:
        """Generate TypeScript type definitions."""
        lines = ["// Auto-generated types from OpenAPI spec", ""]
        for name, schema in self._schemas.items():
            lines.append(f"export interface {name} {{")
            props = schema.get("properties", {})
            required = schema.get("required", [])
            for prop_name, prop_schema in props.items():
                ts_type = self._openapi_to_ts_type(prop_schema)
                optional = "" if prop_name in required else "?"
                lines.append(f"  {prop_name}{optional}: {ts_type};")
            lines.append("}")
            lines.append("")
        return "\n".join(lines)

    def _openapi_to_ts_type(self, schema: dict[str, Any]) -> str:
        """Convert OpenAPI type to TypeScript."""
        type_map = {
            "string": "string",
            "integer": "number",
            "number": "number",
            "boolean": "boolean",
            "array": "any[]",
            "object": "Record<string, any>"
        }
        return type_map.get(schema.get("type", "any"), "any")

    def _generate_ts_client(self, config: SDKConfig) -> str:
        """Generate TypeScript API client."""
        return f'''import axios, {{ AxiosInstance }} from "axios";

export class APIClient {{
  private client: AxiosInstance;

  constructor(baseURL: string = "{config.base_url}") {{
    this.client = axios.create({{ baseURL }});
  }}

  setAuthToken(token: string): void {{
    this.client.defaults.headers.common["Authorization"] = `Bearer ${{token}}`;
  }}
}}
'''


    def _generate_python(self, config: SDKConfig) -> list[GeneratedFile]:
        """Generate Python SDK."""
        files: list[GeneratedFile] = []

        # pyproject.toml
        pyproject = f'''[project]
name = "{config.package_name}"
version = "{config.version}"
description = "{config.description}"
dependencies = ["httpx>=0.25.0", "pydantic>=2.0.0"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
'''
        files.append(GeneratedFile(
            path="pyproject.toml",
            content=pyproject,
            language=SDKLanguage.PYTHON
        ))

        # Models
        models_content = self._generate_python_models()
        files.append(GeneratedFile(
            path="src/models.py",
            content=models_content,
            language=SDKLanguage.PYTHON
        ))

        # Client
        client_content = self._generate_python_client(config)
        files.append(GeneratedFile(
            path="src/client.py",
            content=client_content,
            language=SDKLanguage.PYTHON
        ))

        return files

    def _generate_python_models(self) -> str:
        """Generate Python Pydantic models."""
        lines = [
            '"""Auto-generated models from OpenAPI spec."""',
            "from pydantic import BaseModel",
            "from typing import Any",
            ""
        ]
        for name, schema in self._schemas.items():
            lines.append(f"class {name}(BaseModel):")
            props = schema.get("properties", {})
            if not props:
                lines.append("    pass")
            for prop_name, prop_schema in props.items():
                py_type = self._openapi_to_python_type(prop_schema)
                lines.append(f"    {prop_name}: {py_type}")
            lines.append("")
        return "\n".join(lines)

    def _openapi_to_python_type(self, schema: dict[str, Any]) -> str:
        """Convert OpenAPI type to Python."""
        type_map = {
            "string": "str",
            "integer": "int",
            "number": "float",
            "boolean": "bool",
            "array": "list[Any]",
            "object": "dict[str, Any]"
        }
        return type_map.get(schema.get("type", "Any"), "Any")

    def _generate_python_client(self, config: SDKConfig) -> str:
        """Generate Python API client."""
        return f'''"""Auto-generated API client."""
import httpx
from typing import Any


class APIClient:
    """API client for {config.package_name}."""

    def __init__(self, base_url: str = "{config.base_url}") -> None:
        self._base_url = base_url
        self._client = httpx.Client(base_url=base_url)
        self._token: str | None = None

    def set_auth_token(self, token: str) -> None:
        """Set authentication token."""
        self._token = token
        self._client.headers["Authorization"] = f"Bearer {{token}}"

    def close(self) -> None:
        """Close the client."""
        self._client.close()

    def __enter__(self) -> "APIClient":
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()
'''

    def _generate_go(self, config: SDKConfig) -> list[GeneratedFile]:
        """Generate Go SDK."""
        files: list[GeneratedFile] = []

        # go.mod
        go_mod = f'''module {config.package_name}

go 1.21

require (
    github.com/go-resty/resty/v2 v2.10.0
)
'''
        files.append(GeneratedFile(
            path="go.mod",
            content=go_mod,
            language=SDKLanguage.GO
        ))

        # Client
        client_content = self._generate_go_client(config)
        files.append(GeneratedFile(
            path="client.go",
            content=client_content,
            language=SDKLanguage.GO
        ))

        return files

    def _generate_go_client(self, config: SDKConfig) -> str:
        """Generate Go API client."""
        return f'''package {config.package_name.replace("-", "_")}

import (
    "github.com/go-resty/resty/v2"
)

type Client struct {{
    client  *resty.Client
    baseURL string
}}

func NewClient(baseURL string) *Client {{
    return &Client{{
        client:  resty.New(),
        baseURL: baseURL,
    }}
}}

func (c *Client) SetAuthToken(token string) {{
    c.client.SetAuthToken(token)
}}
'''
