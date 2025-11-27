#!/usr/bin/env python
"""Generate markdown documentation for configuration settings.

Usage:
    python scripts/generate_config_docs.py
    python scripts/generate_config_docs.py --output docs/configuration.md

**Feature: advanced-reusability**
**Validates: Requirements 8.3**
"""

import argparse
import sys
from pathlib import Path
from typing import Any, get_type_hints

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def get_field_info(model_class: type) -> list[dict[str, Any]]:
    """Extract field information from a Pydantic model.

    Args:
        model_class: Pydantic model class.

    Returns:
        List of field info dictionaries.
    """
    fields = []

    for name, field_info in model_class.model_fields.items():
        field_data = {
            "name": name,
            "type": str(field_info.annotation),
            "default": field_info.default if field_info.default is not None else "Required",
            "description": field_info.description or "No description",
            "required": field_info.is_required(),
        }

        # Handle constraints
        constraints = []
        if hasattr(field_info, "ge") and field_info.ge is not None:
            constraints.append(f"min: {field_info.ge}")
        if hasattr(field_info, "le") and field_info.le is not None:
            constraints.append(f"max: {field_info.le}")
        if hasattr(field_info, "min_length") and field_info.min_length is not None:
            constraints.append(f"min_length: {field_info.min_length}")
        if hasattr(field_info, "max_length") and field_info.max_length is not None:
            constraints.append(f"max_length: {field_info.max_length}")
        if hasattr(field_info, "pattern") and field_info.pattern is not None:
            constraints.append(f"pattern: {field_info.pattern}")

        # Check metadata for constraints
        if field_info.metadata:
            for meta in field_info.metadata:
                if hasattr(meta, "ge") and meta.ge is not None:
                    constraints.append(f"min: {meta.ge}")
                if hasattr(meta, "le") and meta.le is not None:
                    constraints.append(f"max: {meta.le}")
                if hasattr(meta, "min_length") and meta.min_length is not None:
                    constraints.append(f"min_length: {meta.min_length}")

        field_data["constraints"] = ", ".join(constraints) if constraints else "None"
        fields.append(field_data)

    return fields


def generate_markdown(settings_class: type) -> str:
    """Generate markdown documentation for settings.

    Args:
        settings_class: The Settings class to document.

    Returns:
        Markdown string.
    """
    lines = [
        "# Configuration Reference",
        "",
        "This document describes all configuration options for the API.",
        "",
        "## Environment Variables",
        "",
        "Configuration is loaded from environment variables. Nested settings use `__` as delimiter.",
        "",
        "Example: `DATABASE__POOL_SIZE=10`",
        "",
    ]

    # Document main settings
    lines.extend([
        "## Application Settings",
        "",
        "| Variable | Type | Default | Description |",
        "|----------|------|---------|-------------|",
    ])

    for field in get_field_info(settings_class):
        if field["name"] not in ["database", "security", "observability"]:
            default = field["default"]
            if default == "Required":
                default = "**Required**"
            lines.append(
                f"| `{field['name'].upper()}` | {field['type']} | {default} | {field['description']} |"
            )

    lines.append("")

    # Document nested settings
    nested_settings = [
        ("database", "Database Settings", "DATABASE__"),
        ("security", "Security Settings", "SECURITY__"),
        ("observability", "Observability Settings", "OBSERVABILITY__"),
    ]

    for attr_name, title, prefix in nested_settings:
        if hasattr(settings_class, "model_fields") and attr_name in settings_class.model_fields:
            field_info = settings_class.model_fields[attr_name]
            nested_class = field_info.default_factory

            if nested_class:
                lines.extend([
                    f"## {title}",
                    "",
                    f"Environment variable prefix: `{prefix}`",
                    "",
                    "| Variable | Type | Default | Description | Constraints |",
                    "|----------|------|---------|-------------|-------------|",
                ])

                for field in get_field_info(nested_class):
                    default = field["default"]
                    if default == "Required":
                        default = "**Required**"
                    elif hasattr(default, "get_secret_value"):
                        default = "**Secret**"

                    lines.append(
                        f"| `{prefix}{field['name'].upper()}` | {field['type']} | {default} | {field['description']} | {field['constraints']} |"
                    )

                lines.append("")

    # Add examples section
    lines.extend([
        "## Example .env File",
        "",
        "```bash",
        "# Application",
        "APP_NAME=My API",
        "DEBUG=false",
        "VERSION=1.0.0",
        "",
        "# Database",
        "DATABASE__URL=postgresql+asyncpg://user:pass@localhost/mydb",
        "DATABASE__POOL_SIZE=10",
        "DATABASE__MAX_OVERFLOW=20",
        "",
        "# Security",
        "SECURITY__SECRET_KEY=your-secret-key-at-least-32-characters-long",
        "SECURITY__CORS_ORIGINS=[\"http://localhost:3000\"]",
        "SECURITY__RATE_LIMIT=100/minute",
        "",
        "# Observability",
        "OBSERVABILITY__LOG_LEVEL=INFO",
        "OBSERVABILITY__LOG_FORMAT=json",
        "OBSERVABILITY__OTLP_ENDPOINT=http://localhost:4317",
        "OBSERVABILITY__SERVICE_NAME=my-api",
        "```",
        "",
        "## Notes",
        "",
        "- All sensitive values (passwords, secrets) should use `SecretStr` type",
        "- Secret values are automatically redacted in logs and string representations",
        "- Invalid configuration will cause the application to fail fast at startup",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Generate configuration documentation"
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        help="Output file path (default: stdout)",
    )

    args = parser.parse_args()

    # Import settings
    from my_api.core.config import Settings

    # Generate documentation
    markdown = generate_markdown(Settings)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown)
        print(f"✓ Configuration documentation written to {output_path}")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
