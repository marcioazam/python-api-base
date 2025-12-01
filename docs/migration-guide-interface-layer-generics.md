# Migration Guide: Interface Layer Generics Review

## Overview

This guide documents the breaking changes and migration steps for the interface layer generics review refactoring.

## Breaking Changes

### 1. Unified Result Type

**Before:**
```python
from src.interface.api.generic_crud.service import ServiceResult

result = ServiceResult(success=True, data=user)
if result.success:
    user = result.data
```

**After:**
```python
from src.shared import Ok, Err, Result

result: Result[User, ServiceError] = Ok(user)
if result.is_ok():
    user = result.unwrap()
```

### 2. Status Enums

**Before:**
```python
# Multiple scattered status enums
from module_a import StatusA
from module_b import StatusB
```

**After:**
```python
from src.interface.api.status import (
    OperationStatus,
    HealthStatus,
    DeliveryStatus,
    PollStatus,
    CompositionStatus,
)
```

### 3. Error Messages

**Before:**
```python
error_message = "User not found"
```

**After:**
```python
from src.interface.api.errors import ErrorMessage, ErrorCode

error = ErrorMessage.not_found("User", user_id)
# Returns structured error with code, message, and details
```

### 4. Builder Pattern

**Before:**
```python
class MyBuilder:
    def build(self):
        return MyObject(...)
```

**After:**
```python
from src.interface.api.patterns import FluentBuilder

class MyBuilder(FluentBuilder[MyObject]):
    def validate(self) -> list[str]:
        errors = []
        errors.extend(self._validate_required("field", self._field))
        return errors
    
    def _do_build(self) -> MyObject:
        return MyObject(...)
```

### 5. Transformer Pattern

**Before:**
```python
def transform(data):
    return modified_data
```

**After:**
```python
from src.interface.api.transformers import BaseTransformer, TransformationContext

class MyTransformer(BaseTransformer[InputType, OutputType]):
    def transform(self, data: InputType, context: TransformationContext) -> OutputType:
        return modified_data
```

## Type Aliases

New centralized type aliases in `src/interface/api/types.py`:

```python
type HandlerFunc[T, R] = Callable[[T], Awaitable[R]]
type ServiceResult[T] = Result[T, ServiceError]
type RepositoryResult[T] = Result[T, RepositoryError]
type ValidationRule[T] = Callable[[T], list[str]]
type Hook[T] = Callable[[T], T]
```

## Import Changes

### Old Imports → New Imports

| Old Import | New Import |
|------------|------------|
| `from module.service import ServiceResult` | `from src.shared import Result, Ok, Err` |
| `from module.status import Status` | `from src.interface.api.status import OperationStatus` |
| `from module.errors import ErrorMessage` | `from src.interface.api.errors import ErrorMessage` |
| `from module.builder import Builder` | `from src.interface.api.patterns import FluentBuilder` |

## Testing

All property-based tests are in `tests/properties/test_interface_layer_generics_properties.py`.

Run tests:
```bash
python -m pytest tests/properties/test_interface_layer_generics_properties.py -v
```

## Correctness Properties

The following properties are tested:

1. **Result Ok/Err Duality** - Result is either Ok or Err, never both
2. **Result Unwrap Safety** - Ok.unwrap() returns value, Err.unwrap() raises
3. **Result Map Preservation** - map preserves Ok/Err state correctly
4. **Result Unwrap_or Default** - unwrap_or returns value or default
5. **Status Enum Snake Case** - All status values are snake_case
6. **Transformer Chain Composition** - Composite transformer equals sequential
7. **Identity Transformer Preservation** - Identity returns input unchanged
8. **Builder Fluent Return** - Builder methods return self
9. **Error Message Factory Consistency** - Factory methods produce consistent structure
10. **Pagination Result Consistency** - has_next/has_prev are correct
11. **Cursor Round Trip** - encode/decode cursor preserves value
12. **HMAC Signature Verification** - Signatures verify correctly
13. **JSON-RPC Error Codes** - Error codes are in valid range
14. **Poll Timeout Result** - Timeout returns correct status
15. **Dataclass Slots Efficiency** - Slots dataclasses have no __dict__
16. **Protocol Runtime Checkable** - isinstance works with protocols
17. **Structured Logging Extra Dict** - Log extra contains required fields
18. **Problem Details Structure** - RFC 7807 fields are present
19. **CSP Builder Strict Defaults** - Strict policy has correct defaults
20. **WebSocket Message Type Safety** - Messages are type-safe
