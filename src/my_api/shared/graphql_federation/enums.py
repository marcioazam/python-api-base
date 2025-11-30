"""graphql_federation enums."""

from __future__ import annotations

from enum import Enum


class FederationDirective(str, Enum):
    """Apollo Federation directives."""

    KEY = "@key"
    EXTERNAL = "@external"
    REQUIRES = "@requires"
    PROVIDES = "@provides"
    EXTENDS = "@extends"
    SHAREABLE = "@shareable"
    INACCESSIBLE = "@inaccessible"
    OVERRIDE = "@override"
    TAG = "@tag"
