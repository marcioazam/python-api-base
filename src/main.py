"""FastAPI application entry point.

This module provides the main application factory and lifespan management.
"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.config import get_settings
from infrastructure.di import lifecycle
from interface.v1.health_router import router as health_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan manager.

    Handles startup and shutdown events using the lifecycle manager.
    """
    settings = get_settings()
    app.state.settings = settings

    lifecycle.run_startup()
    await lifecycle.run_startup_async()

    yield

    await lifecycle.run_shutdown_async()
    lifecycle.run_shutdown()


def _configure_middleware(app: FastAPI) -> None:
    """Configure all middleware for the application."""
    settings = get_settings()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.security.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=settings.version,
        description="Modern REST API Framework",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    _configure_middleware(app)
    app.include_router(health_router)

    return app


app = create_app()


if __name__ == "__main__":
    import os

    import uvicorn

    host = os.getenv("API_HOST", "127.0.0.1")
    port = int(os.getenv("API_PORT", "8000"))
    uvicorn.run("main:app", host=host, port=port, reload=True)
