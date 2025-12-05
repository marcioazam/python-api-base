"""GraphQL resolvers.

Contains resolver functions and data loaders.

**Feature: interface-restructuring-2025**
"""

from interface.graphql.resolvers.dataloader import DataLoaderService
from interface.graphql.resolvers.resolvers import resolve_user, resolve_users

__all__ = [
    "DataLoaderService",
    "resolve_user",
    "resolve_users",
]
