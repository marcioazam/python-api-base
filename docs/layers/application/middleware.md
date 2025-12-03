# Application Middleware

## Overview

Application middleware provides cross-cutting concerns for use case execution.

## Middleware Types

### Logging Middleware

```python
class LoggingMiddleware:
    """Logs use case execution."""
    
    async def execute(self, use_case, next):
        logger.info("Executing", use_case=type(use_case).__name__)
        try:
            result = await next(use_case)
            logger.info("Completed", use_case=type(use_case).__name__)
            return result
        except Exception as e:
            logger.error("Failed", use_case=type(use_case).__name__, error=str(e))
            raise
```

### Validation Middleware

```python
class ValidationMiddleware:
    """Validates use case input."""
    
    async def execute(self, use_case, next):
        if hasattr(use_case, "validate"):
            use_case.validate()
        return await next(use_case)
```

### Transaction Middleware

```python
class TransactionMiddleware:
    """Wraps use case in transaction."""
    
    async def execute(self, use_case, next):
        async with self.uow:
            result = await next(use_case)
            await self.uow.commit()
            return result
```

## Pipeline

```python
pipeline = Pipeline([
    LoggingMiddleware(),
    ValidationMiddleware(),
    TransactionMiddleware(),
])

result = await pipeline.execute(use_case)
```

## Related

- [CQRS](cqrs.md)
- [Interface Middleware](../interface/middleware.md)
