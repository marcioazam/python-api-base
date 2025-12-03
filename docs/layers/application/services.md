# Application Services

## Overview

Application Services são serviços cross-cutting que fornecem funcionalidades compartilhadas como feature flags, multitenancy e file upload.

## Feature Flags Service

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class FeatureFlag:
    """Feature flag definition."""
    name: str
    enabled: bool
    percentage: int = 100  # Rollout percentage
    conditions: dict[str, Any] | None = None

class FeatureFlagService:
    """Service for managing feature flags."""
    
    def __init__(self, store: FeatureFlagStore):
        self._store = store
    
    async def is_enabled(
        self,
        flag_name: str,
        context: dict[str, Any] | None = None,
    ) -> bool:
        flag = await self._store.get(flag_name)
        if flag is None:
            return False
        
        if not flag.enabled:
            return False
        
        # Check percentage rollout
        if flag.percentage < 100:
            if not self._check_percentage(flag, context):
                return False
        
        # Check conditions
        if flag.conditions and context:
            if not self._check_conditions(flag.conditions, context):
                return False
        
        return True
    
    def _check_percentage(self, flag: FeatureFlag, context: dict | None) -> bool:
        # Use user_id for consistent rollout
        user_id = context.get("user_id", "") if context else ""
        hash_value = hash(f"{flag.name}:{user_id}") % 100
        return hash_value < flag.percentage
```

### Usage

```python
@router.get("/new-feature")
async def new_feature(
    feature_flags: FeatureFlagService = Depends(get_feature_flags),
    current_user: User = Depends(get_current_user),
):
    if not await feature_flags.is_enabled("new_feature", {"user_id": current_user.id}):
        raise HTTPException(404, "Feature not available")
    
    return {"message": "New feature enabled!"}
```

## Multitenancy Service

```python
from contextvars import ContextVar

tenant_context: ContextVar[str | None] = ContextVar("tenant_id", default=None)

class TenantService:
    """Service for managing tenant context."""
    
    @staticmethod
    def get_current_tenant() -> str | None:
        return tenant_context.get()
    
    @staticmethod
    def set_current_tenant(tenant_id: str) -> None:
        tenant_context.set(tenant_id)
    
    @staticmethod
    def clear_tenant() -> None:
        tenant_context.set(None)

class TenantMiddleware:
    """Middleware to extract tenant from request."""
    
    async def __call__(self, request: Request, call_next):
        # Extract tenant from header or subdomain
        tenant_id = request.headers.get("X-Tenant-ID")
        if not tenant_id:
            tenant_id = self._extract_from_subdomain(request.url.host)
        
        if tenant_id:
            TenantService.set_current_tenant(tenant_id)
        
        try:
            response = await call_next(request)
            return response
        finally:
            TenantService.clear_tenant()
```

### Tenant-Aware Repository

```python
class TenantAwareRepository[T](AsyncRepository[T, str]):
    """Repository that filters by tenant."""
    
    def __init__(self, session: AsyncSession, model: type[T]):
        self._session = session
        self._model = model
    
    async def get(self, id: str) -> T | None:
        tenant_id = TenantService.get_current_tenant()
        result = await self._session.execute(
            select(self._model).where(
                self._model.id == id,
                self._model.tenant_id == tenant_id,
            )
        )
        return result.scalar_one_or_none()
```

## File Upload Service

```python
from dataclasses import dataclass
from pathlib import Path
import hashlib

@dataclass
class FileInfo:
    """Information about uploaded file."""
    filename: str
    content_type: str
    size: int
    checksum: str
    url: str

class FileUploadService:
    """Service for handling file uploads."""
    
    def __init__(
        self,
        storage: FileStorage,
        allowed_types: list[str],
        max_size: int,
    ):
        self._storage = storage
        self._allowed_types = allowed_types
        self._max_size = max_size
    
    async def upload(
        self,
        file: UploadFile,
        folder: str = "uploads",
    ) -> FileInfo:
        # Validate
        self._validate_file(file)
        
        # Read content
        content = await file.read()
        
        # Generate unique filename
        checksum = hashlib.sha256(content).hexdigest()[:16]
        ext = Path(file.filename).suffix
        unique_name = f"{checksum}{ext}"
        
        # Upload to storage
        url = await self._storage.upload(
            path=f"{folder}/{unique_name}",
            content=content,
            content_type=file.content_type,
        )
        
        return FileInfo(
            filename=file.filename,
            content_type=file.content_type,
            size=len(content),
            checksum=checksum,
            url=url,
        )
    
    def _validate_file(self, file: UploadFile) -> None:
        if file.content_type not in self._allowed_types:
            raise ValidationError(f"File type {file.content_type} not allowed")
        
        if file.size > self._max_size:
            raise ValidationError(f"File size exceeds {self._max_size} bytes")
```

## Notification Service

```python
from abc import ABC, abstractmethod
from enum import Enum

class NotificationChannel(Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"

@dataclass
class Notification:
    recipient: str
    subject: str
    body: str
    channel: NotificationChannel
    metadata: dict[str, Any] | None = None

class NotificationService:
    """Service for sending notifications."""
    
    def __init__(self, providers: dict[NotificationChannel, NotificationProvider]):
        self._providers = providers
    
    async def send(self, notification: Notification) -> bool:
        provider = self._providers.get(notification.channel)
        if not provider:
            raise ValueError(f"No provider for {notification.channel}")
        
        return await provider.send(notification)
    
    async def send_welcome_email(self, user: User) -> bool:
        return await self.send(Notification(
            recipient=user.email,
            subject="Welcome!",
            body=f"Hello {user.name}, welcome to our platform!",
            channel=NotificationChannel.EMAIL,
        ))
```

## Best Practices

1. **Use dependency injection** - For testability
2. **Keep services stateless** - Use context vars for request-scoped state
3. **Define clear interfaces** - Use protocols
4. **Handle errors gracefully** - Return Result types
5. **Log operations** - For debugging and auditing
