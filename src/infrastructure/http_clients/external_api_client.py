"""Generic external API client."""
from typing import Any
from my_app.infrastructure.http_clients.base_client import BaseHTTPClient, ClientConfig

class ExternalAPIClient(BaseHTTPClient):
    def __init__(self, base_url: str, api_key: str | None = None) -> None:
        super().__init__(ClientConfig(base_url=base_url))
        self._api_key = api_key
    
    async def fetch(self, endpoint: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        return await self.get(endpoint, params=params)
    
    async def submit(self, endpoint: str, data: dict[str, Any]) -> dict[str, Any]:
        return await self.post(endpoint, data)
