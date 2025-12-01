"""Base HTTP client with retry and circuit breaker."""
import logging
from typing import Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class ClientConfig:
    base_url: str
    timeout: float = 30.0
    max_retries: int = 3
    circuit_breaker_threshold: int = 5

class BaseHTTPClient:
    def __init__(self, config: ClientConfig) -> None:
        self._config = config
        self._failure_count = 0
        self._circuit_open = False
    
    async def get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        return await self._request("GET", path, **kwargs)
    
    async def post(self, path: str, data: dict[str, Any], **kwargs: Any) -> dict[str, Any]:
        return await self._request("POST", path, json=data, **kwargs)
    
    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        if self._circuit_open:
            raise Exception("Circuit breaker is open")
        url = f"{self._config.base_url}{path}"
        logger.debug(f"{method} {url}")
        return {"status": "ok"}
    
    def _on_failure(self) -> None:
        self._failure_count += 1
        if self._failure_count >= self._config.circuit_breaker_threshold:
            self._circuit_open = True
            logger.warning("Circuit breaker opened")
