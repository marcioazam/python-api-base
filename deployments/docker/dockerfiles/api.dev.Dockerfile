# =============================================================================
# Development Dockerfile for Python API Base
# =============================================================================
#
# Features:
#   - Hot reload support
#   - Debug tools included
#   - Full dev dependencies
#   - Volume mount friendly
#
# Build: docker build -f deployments/docker/dockerfiles/api.dev.Dockerfile -t python-api:dev .
#
# =============================================================================

FROM python:3.12-slim

LABEL org.opencontainers.image.title="Python API Base (Development)"

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* README.md ./

# Install all dependencies including dev
ENV UV_SYSTEM_PYTHON=1
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache ".[dev]"

# Set environment
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=development

# Expose ports (API + debugger)
EXPOSE 8000 5678

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD curl -f http://localhost:8000/health/live || exit 1

# Development: Run with hot reload
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
