"""Cloud Provider IP Filtering.

**Feature: code-review-refactoring, Task 16.2: Refactor cloud_provider_filter.py**
**Validates: Requirements 5.2**

Original: cloud_provider_filter.py (456 lines)
Refactored: cloud_provider_filter/ package

Provides filtering to block or allow requests from cloud provider IP ranges.
"""

from .enums import CloudProvider
from .models import CloudProviderInfo, CloudProviderResult
from .config import CloudProviderConfig
from .ranges import DEFAULT_CLOUD_RANGES, CloudIPRangeProvider, InMemoryCloudRangeProvider
from .filter import CloudProviderFilter, CloudProviderFilterBuilder, create_cloud_filter

__all__ = [
    "CloudProvider",
    "CloudProviderInfo",
    "CloudProviderResult",
    "CloudProviderConfig",
    "CloudIPRangeProvider",
    "InMemoryCloudRangeProvider",
    "DEFAULT_CLOUD_RANGES",
    "CloudProviderFilter",
    "CloudProviderFilterBuilder",
    "create_cloud_filter",
]
