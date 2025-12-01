"""API Composition Pattern Implementation.

This module provides API composition for aggregating multiple API calls
with parallel and sequential execution strategies.

**Feature: api-architecture-analysi

Feature: file-size-compliance-phase2
"""

from .enums import *
from .models import *
from .config import *
from .constants import *
from .service import *

__all__ = ['APICallConfig', 'APIComposer', 'AggregatedResponse', 'CallResult', 'CompositionBuilder', 'CompositionResult', 'CompositionStatus', 'ExecutionStrategy', 'T', 'aggregate', 'compose_parallel', 'compose_sequential']
