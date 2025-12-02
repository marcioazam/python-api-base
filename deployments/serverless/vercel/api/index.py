"""Vercel Serverless Function handler.

**Feature: serverless-adapters**
**Requirement: Serverless-ready deployment (Vercel)**

This module provides a Vercel-compatible handler that wraps the FastAPI
application. Vercel supports Python serverless functions natively.

Deployment:
    1. Copy this file to api/index.py in your project root
    2. Add vercel.json configuration
    3. Deploy with `vercel`
"""

from __future__ import annotations

import os
import sys

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "src"))

# Set environment for serverless
os.environ.setdefault("ENVIRONMENT", "vercel")


def get_app():
    """Get or create FastAPI application.

    Lazy import to reduce cold start time.
    """
    from main import create_app

    return create_app()


# Export app for Vercel
app = get_app()

# Vercel expects the handler to be named 'handler' or 'app'
handler = app
