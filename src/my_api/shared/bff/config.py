"""bff configuration."""

from dataclasses import dataclass, field
from typing import Any
from .enums import ClientType


@dataclass
class FieldConfig:
    """Configuration for field inclusion/exclusion."""

    include: set[str] = field(default_factory=set)
    exclude: set[str] = field(default_factory=set)
    rename: dict[str, str] = field(default_factory=dict)

    def apply(self, data: dict[str, Any]) -> dict[str, Any]:
        """Apply field configuration to data."""
        result = {}

        for key, value in data.items():
            # Check exclusion
            if self.exclude and key in self.exclude:
                continue

            # Check inclusion (if specified, only include listed fields)
            if self.include and key not in self.include:
                continue

            # Apply rename
            new_key = self.rename.get(key, key)
            result[new_key] = value

        return result

@dataclass
class ClientConfig:
    """Configuration for a specific client type."""

    client_type: ClientType
    fields: FieldConfig = field(default_factory=FieldConfig)
    max_list_size: int = 100
    include_metadata: bool = True
    compress_images: bool = False
    image_quality: int = 80
    pagination_style: str = "offset"  # offset, cursor
    date_format: str = "iso"  # iso, unix, relative

class BFFConfig:
    """Configuration for BFF routing."""

    def __init__(self) -> None:
        self._configs: dict[ClientType, ClientConfig] = {}
        self._default_config = ClientConfig(client_type=ClientType.UNKNOWN)

    def configure(self, client_type: ClientType, config: ClientConfig) -> "BFFConfig":
        """Configure settings for a client type."""
        self._configs[client_type] = config
        return self

    def get_config(self, client_type: ClientType) -> ClientConfig:
        """Get configuration for a client type."""
        return self._configs.get(client_type, self._default_config)

    def set_default(self, config: ClientConfig) -> "BFFConfig":
        """Set default configuration."""
        self._default_config = config
        return self

class BFFConfigBuilder:
    """Builder for BFF configuration."""

    def __init__(self) -> None:
        self._config = BFFConfig()

    def for_mobile(
        self,
        max_list_size: int = 20,
        exclude_fields: set[str] | None = None,
        compress_images: bool = True,
    ) -> "BFFConfigBuilder":
        """Configure mobile client settings."""
        config = ClientConfig(
            client_type=ClientType.MOBILE,
            fields=FieldConfig(exclude=exclude_fields or set()),
            max_list_size=max_list_size,
            compress_images=compress_images,
            image_quality=60,
            pagination_style="cursor",
        )
        self._config.configure(ClientType.MOBILE, config)
        return self

    def for_web(
        self,
        max_list_size: int = 50,
        exclude_fields: set[str] | None = None,
    ) -> "BFFConfigBuilder":
        """Configure web client settings."""
        config = ClientConfig(
            client_type=ClientType.WEB,
            fields=FieldConfig(exclude=exclude_fields or set()),
            max_list_size=max_list_size,
            include_metadata=True,
            pagination_style="offset",
        )
        self._config.configure(ClientType.WEB, config)
        return self

    def for_desktop(
        self,
        max_list_size: int = 100,
        include_metadata: bool = True,
    ) -> "BFFConfigBuilder":
        """Configure desktop client settings."""
        config = ClientConfig(
            client_type=ClientType.DESKTOP,
            max_list_size=max_list_size,
            include_metadata=include_metadata,
        )
        self._config.configure(ClientType.DESKTOP, config)
        return self

    def for_api(
        self,
        max_list_size: int = 1000,
        date_format: str = "iso",
    ) -> "BFFConfigBuilder":
        """Configure API client settings."""
        config = ClientConfig(
            client_type=ClientType.API,
            max_list_size=max_list_size,
            include_metadata=True,
            date_format=date_format,
        )
        self._config.configure(ClientType.API, config)
        return self

    def build(self) -> BFFConfig:
        """Build the configuration."""
        return self._config
