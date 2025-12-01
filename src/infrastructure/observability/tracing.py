"""OpenTelemetry tracing setup."""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class TracingConfig:
    service_name: str = "my_app"
    endpoint: str = "http://localhost:4317"
    enabled: bool = True


class TracingProvider:
    def __init__(self, config: TracingConfig | None = None) -> None:
        self._config = config or TracingConfig()
        self._tracer = None

    def setup(self) -> None:
        if not self._config.enabled:
            logger.info("Tracing disabled")
            return
        logger.info(f"Setting up tracing for {self._config.service_name}")

    def get_tracer(self) -> Any:
        return self._tracer

    def create_span(self, name: str) -> Any:
        logger.debug(f"Creating span: {name}")
        return None

    def shutdown(self) -> None:
        logger.info("Shutting down tracing")
