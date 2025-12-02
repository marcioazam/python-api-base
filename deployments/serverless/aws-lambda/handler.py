"""AWS Lambda handler adapter for FastAPI application.

**Feature: serverless-adapters**
**Requirement: Serverless-ready deployment**

This module provides a Lambda-compatible handler that wraps the FastAPI
application using Mangum for AWS API Gateway integration.

Usage:
    Deploy with SAM, Serverless Framework, or CDK pointing to
    `deployments.serverless.aws_lambda.handler.handler`
"""

from __future__ import annotations

import logging
import os
from typing import Any

# Configure logging for Lambda
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def get_app():
    """Get or create FastAPI application.

    Lazy import to reduce cold start time.
    """
    # Set environment for serverless
    os.environ.setdefault("ENVIRONMENT", "lambda")

    from main import create_app

    return create_app()


# Initialize Mangum adapter
try:
    from mangum import Mangum

    # Create handler with API Gateway v2 (HTTP API) support
    app = get_app()
    handler = Mangum(
        app,
        lifespan="auto",
        api_gateway_base_path=os.getenv("API_GATEWAY_BASE_PATH", ""),
    )

except ImportError:
    logger.warning("Mangum not installed. Lambda handler unavailable.")

    async def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
        """Fallback handler when Mangum is not available."""
        return {
            "statusCode": 500,
            "body": '{"error": "Mangum not installed"}',
            "headers": {"Content-Type": "application/json"},
        }


# =============================================================================
# Alternative: Custom Lambda Handler (without Mangum)
# =============================================================================


class LambdaAdapter:
    """Custom Lambda adapter for more control.

    Use this instead of Mangum if you need custom request/response handling.
    """

    def __init__(self, app) -> None:
        """Initialize adapter.

        Args:
            app: FastAPI application
        """
        self._app = app

    async def __call__(
        self,
        event: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        """Handle Lambda invocation.

        Supports both API Gateway REST API (v1) and HTTP API (v2) events.

        Args:
            event: Lambda event
            context: Lambda context

        Returns:
            API Gateway response
        """
        from starlette.testclient import TestClient

        # Detect event version
        version = event.get("version", "1.0")

        if version == "2.0":
            return await self._handle_v2(event, context)
        else:
            return await self._handle_v1(event, context)

    async def _handle_v1(
        self,
        event: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        """Handle API Gateway REST API (v1) event."""
        method = event.get("httpMethod", "GET")
        path = event.get("path", "/")
        headers = event.get("headers", {}) or {}
        query_params = event.get("queryStringParameters", {}) or {}
        body = event.get("body", "")

        # Build query string
        query_string = "&".join(f"{k}={v}" for k, v in query_params.items())
        full_path = f"{path}?{query_string}" if query_string else path

        # Make request
        with TestClient(self._app) as client:
            response = client.request(
                method=method,
                url=full_path,
                headers=headers,
                content=body,
            )

        return {
            "statusCode": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "isBase64Encoded": False,
        }

    async def _handle_v2(
        self,
        event: dict[str, Any],
        context: Any,
    ) -> dict[str, Any]:
        """Handle API Gateway HTTP API (v2) event."""
        request_context = event.get("requestContext", {})
        http = request_context.get("http", {})

        method = http.get("method", "GET")
        path = event.get("rawPath", "/")
        headers = event.get("headers", {}) or {}
        query_string = event.get("rawQueryString", "")
        body = event.get("body", "")

        full_path = f"{path}?{query_string}" if query_string else path

        with TestClient(self._app) as client:
            response = client.request(
                method=method,
                url=full_path,
                headers=headers,
                content=body,
            )

        return {
            "statusCode": response.status_code,
            "headers": dict(response.headers),
            "body": response.text,
            "isBase64Encoded": False,
        }


# Export custom handler for advanced use cases
custom_handler = LambdaAdapter(get_app())
