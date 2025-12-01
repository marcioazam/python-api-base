"""Generic Entity Factory with PEP 695 type parameters.

**Feature: python-api-base-2025-state-of-art**
**Validates: Requirements 27.1, 27.2**
"""

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable
from pydantic import BaseModel


@runtime_checkable
class Factory[T](Protocol):
    """Protocol for entity factories.
    
    Type Parameters:
        T: The type of entity to create.
    """
    
    def build(self, **overrides: Any) -> T:
        """Build an entity with optional overrides."""
        ...


@runtime_checkable
class AsyncFactory[T](Protocol):
    """Protocol for async entity factories.
    
    Type Parameters:
        T: The type of entity to create.
    """
    
    async def build(self, **overrides: Any) -> T:
        """Build an entity asynchronously with optional overrides."""
        ...


class EntityFactory[T: BaseModel]:
    """Generic factory for Pydantic entities.
    
    Type Parameters:
        T: The Pydantic model type to create.
    
    **Feature: python-api-base-2025-state-of-art**
    **Validates: Requirements 27.1, 27.2**
    """
    
    def __init__(
        self,
        model_class: type[T],
        defaults: dict[str, Any] | None = None,
    ) -> None:
        self._model_class = model_class
        self._defaults = defaults or {}
        self._sequence = 0

    def _next_sequence(self) -> int:
        """Get next sequence number."""
        self._sequence += 1
        return self._sequence
    
    def build(self, **overrides: Any) -> T:
        """Build an entity with optional overrides.
        
        Args:
            **overrides: Field values to override defaults.
            
        Returns:
            New entity instance.
        """
        data = {**self._defaults, **overrides}
        
        # Process callable defaults
        for key, value in data.items():
            if callable(value):
                data[key] = value(self._next_sequence())
        
        return self._model_class(**data)
    
    def build_batch(self, count: int, **overrides: Any) -> list[T]:
        """Build multiple entities.
        
        Args:
            count: Number of entities to create.
            **overrides: Field values to override defaults.
            
        Returns:
            List of new entity instances.
        """
        return [self.build(**overrides) for _ in range(count)]
    
    def with_defaults(self, **defaults: Any) -> "EntityFactory[T]":
        """Create a new factory with additional defaults.
        
        Args:
            **defaults: Additional default values.
            
        Returns:
            New factory with merged defaults.
        """
        merged = {**self._defaults, **defaults}
        return EntityFactory(self._model_class, merged)


class AsyncEntityFactory[T: BaseModel]:
    """Async factory for entities that require async creation.
    
    Type Parameters:
        T: The Pydantic model type to create.
    """
    
    def __init__(
        self,
        model_class: type[T],
        defaults: dict[str, Any] | None = None,
        async_setup: Callable[[T], Any] | None = None,
    ) -> None:
        self._model_class = model_class
        self._defaults = defaults or {}
        self._async_setup = async_setup
        self._sequence = 0
    
    def _next_sequence(self) -> int:
        """Get next sequence number."""
        self._sequence += 1
        return self._sequence
    
    async def build(self, **overrides: Any) -> T:
        """Build an entity asynchronously.
        
        Args:
            **overrides: Field values to override defaults.
            
        Returns:
            New entity instance.
        """
        data = {**self._defaults, **overrides}
        
        # Process callable defaults
        for key, value in data.items():
            if callable(value):
                result = value(self._next_sequence())
                if hasattr(result, '__await__'):
                    data[key] = await result
                else:
                    data[key] = result
        
        entity = self._model_class(**data)
        
        if self._async_setup:
            await self._async_setup(entity)
        
        return entity
    
    async def build_batch(self, count: int, **overrides: Any) -> list[T]:
        """Build multiple entities asynchronously."""
        return [await self.build(**overrides) for _ in range(count)]
