"""GraphQL Federation support for microservices architecture.

Implements Apollo Federation specification for distributed GraphQL schemas.

**Feature: api-architecture-analysis, Property 1: Federation sc

Feature: file-size-compliance-phase2
"""

from .enums import *
from .service import *

__all__ = ['EntityResolver', 'FederatedEntity', 'FederatedField', 'FederatedSchema', 'FederationDirective', 'FederationGateway', 'KeyDirective', 'OverrideDirective', 'ProvidesDirective', 'ReferenceResolver', 'RequiresDirective', 'ServiceDefinition', 'Subgraph', 'create_entity_type', 'create_extended_entity']
