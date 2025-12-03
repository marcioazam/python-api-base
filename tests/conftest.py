"""Pytest configuration - creates my_app alias for src.

**Feature: src-interface-improvements**
**Validates: Requirements 1.1, 1.2, 1.3, 2.1, 2.5**
"""
import importlib
import sys
from pathlib import Path
from typing import Any, Generator
from uuid import uuid4

import pytest

_src = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(_src))

# Register all src submodules as my_app.X
_submodules = ['core', 'application', 'infrastructure', 'interface', 'domain', 'shared']

for sub in _submodules:
    try:
        mod = importlib.import_module(sub)
        sys.modules[f'my_app.{sub}'] = mod
    except ImportError:
        pass

# Create my_app package
import types
my_app = types.ModuleType('my_app')
my_app.__path__ = [str(_src)]
my_app.__file__ = str(_src / '__init__.py')
for sub in _submodules:
    if f'my_app.{sub}' in sys.modules:
        setattr(my_app, sub, sys.modules[f'my_app.{sub}'])
sys.modules['my_app'] = my_app


# =============================================================================
# HTTP Test Infrastructure
# **Feature: src-interface-improvements**
# **Validates: Requirements 1.1, 2.1**
# =============================================================================


@pytest.fixture
def admin_headers() -> dict[str, str]:
    """Headers for authenticated requests with admin role.
    
    **Feature: src-interface-improvements**
    **Validates: Requirements 1.3, 2.5**
    """
    return {
        "X-User-Id": "test-admin",
        "X-User-Roles": "admin",
        "X-Tenant-Id": "test-tenant",
    }


@pytest.fixture
def editor_headers() -> dict[str, str]:
    """Headers for authenticated requests with editor role."""
    return {
        "X-User-Id": "test-editor",
        "X-User-Roles": "editor",
        "X-Tenant-Id": "test-tenant",
    }


@pytest.fixture
def viewer_headers() -> dict[str, str]:
    """Headers for viewer role (read-only)."""
    return {
        "X-User-Id": "test-viewer",
        "X-User-Roles": "viewer",
    }


@pytest.fixture
def tenant_headers() -> dict[str, str]:
    """Headers with specific tenant context."""
    return {
        "X-User-Id": "tenant-user",
        "X-User-Roles": "admin",
        "X-Tenant-Id": f"tenant-{uuid4().hex[:8]}",
    }


@pytest.fixture
def item_data_factory() -> callable:
    """Factory for creating unique item test data.
    
    **Feature: src-interface-improvements**
    **Validates: Requirements 1.2**
    """
    def _create_item_data(
        name: str = "Test Item",
        category: str = "electronics",
        quantity: int = 10,
    ) -> dict[str, Any]:
        return {
            "name": name,
            "sku": f"SKU-{uuid4().hex[:8].upper()}",
            "price": {"amount": "99.99", "currency": "BRL"},
            "quantity": quantity,
            "category": category,
            "tags": ["test", "automated"],
        }
    return _create_item_data


@pytest.fixture
def pedido_data_factory() -> callable:
    """Factory for creating unique pedido test data.
    
    **Feature: src-interface-improvements**
    **Validates: Requirements 2.2**
    """
    def _create_pedido_data(
        customer_name: str = "Test Customer",
        shipping_address: str = "123 Test St",
    ) -> dict[str, Any]:
        return {
            "customer_id": f"cust-{uuid4().hex[:8]}",
            "customer_name": customer_name,
            "customer_email": f"test-{uuid4().hex[:6]}@example.com",
            "shipping_address": shipping_address,
            "notes": "Automated test order",
        }
    return _create_pedido_data
