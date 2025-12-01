"""Backend for Frontend (BFF) Pattern Implementation.

This module provides BFF routing for optimized responses per client type
(mobile, web, desktop, API).

**Feature: api-architecture-analysis**
**Vali

Feature: file-size-compliance-phase2
"""

from .enums import *
from .models import *
from .config import *
from .service import *

__all__ = ['BFFConfig', 'BFFConfigBuilder', 'BFFRoute', 'BFFRouter', 'BaseTransformer', 'ClientConfig', 'ClientInfo', 'ClientType', 'DictTransformer', 'FieldConfig', 'IdentityTransformer', 'ListTransformer', 'ResponseTransformer', 'create_bff_router', 'create_default_bff_config', 'detect_client']
