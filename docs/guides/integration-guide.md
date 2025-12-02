# Guia: Adicionando Integrações

Este guia descreve como adicionar novas integrações de infraestrutura ao Python API Base usando a abordagem protocol-first.

## Abordagem Protocol-First

1. Definir Protocol (interface) em `src/core/protocols/`
2. Implementar Provider em `src/infrastructure/`
3. Registrar no DI Container
4. Criar testes

## Exemplo: Storage Provider

### 1. Definir Protocol

```python
# src/core/protocols/storage.py
from typing import Protocol
from dataclasses import dataclass

@dataclass
class FileInfo:
    key: str
    size: int
    content_type: str
    last_modified: datetime

class StorageProvider(Protocol):
    """Protocol for file storage operations."""

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        """Upload file and return URL."""
        ...

    async def download(self, key: str) -> bytes:
        """Download file content."""
        ...

    async def delete(self, key: str) -> bool:
        """Delete file."""
        ...

    async def exists(self, key: str) -> bool:
        """Check if file exists."""
        ...

    async def get_info(self, key: str) -> FileInfo | None:
        """Get file metadata."""
        ...

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 100,
    ) -> list[FileInfo]:
        """List files with optional prefix filter."""
        ...
```

### 2. Implementar MinIO Provider

```python
# src/infrastructure/storage/minio_provider.py
from minio import Minio
from core.protocols.storage import StorageProvider, FileInfo

class MinIOStorageProvider(StorageProvider):
    def __init__(
        self,
        endpoint: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        secure: bool = True,
    ):
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
        self._bucket = bucket

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        from io import BytesIO

        self._client.put_object(
            self._bucket,
            key,
            BytesIO(data),
            len(data),
            content_type=content_type,
        )
        return f"/{self._bucket}/{key}"

    async def download(self, key: str) -> bytes:
        response = self._client.get_object(self._bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    async def delete(self, key: str) -> bool:
        try:
            self._client.remove_object(self._bucket, key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            self._client.stat_object(self._bucket, key)
            return True
        except Exception:
            return False

    async def get_info(self, key: str) -> FileInfo | None:
        try:
            stat = self._client.stat_object(self._bucket, key)
            return FileInfo(
                key=key,
                size=stat.size,
                content_type=stat.content_type,
                last_modified=stat.last_modified,
            )
        except Exception:
            return None

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 100,
    ) -> list[FileInfo]:
        objects = self._client.list_objects(
            self._bucket,
            prefix=prefix,
        )
        files = []
        for obj in objects:
            if len(files) >= limit:
                break
            files.append(
                FileInfo(
                    key=obj.object_name,
                    size=obj.size,
                    content_type=obj.content_type or "application/octet-stream",
                    last_modified=obj.last_modified,
                )
            )
        return files
```

### 3. Implementar In-Memory Provider (Testing)

```python
# src/infrastructure/storage/memory_provider.py
from core.protocols.storage import StorageProvider, FileInfo

class InMemoryStorageProvider(StorageProvider):
    def __init__(self):
        self._files: dict[str, tuple[bytes, str, datetime]] = {}

    async def upload(
        self,
        key: str,
        data: bytes,
        content_type: str,
    ) -> str:
        self._files[key] = (data, content_type, datetime.utcnow())
        return f"/memory/{key}"

    async def download(self, key: str) -> bytes:
        if key not in self._files:
            raise FileNotFoundError(key)
        return self._files[key][0]

    async def delete(self, key: str) -> bool:
        if key in self._files:
            del self._files[key]
            return True
        return False

    async def exists(self, key: str) -> bool:
        return key in self._files

    async def get_info(self, key: str) -> FileInfo | None:
        if key not in self._files:
            return None
        data, content_type, modified = self._files[key]
        return FileInfo(
            key=key,
            size=len(data),
            content_type=content_type,
            last_modified=modified,
        )

    async def list_files(
        self,
        prefix: str = "",
        limit: int = 100,
    ) -> list[FileInfo]:
        files = []
        for key in self._files:
            if key.startswith(prefix):
                info = await self.get_info(key)
                if info:
                    files.append(info)
                if len(files) >= limit:
                    break
        return files
```

### 4. Registrar no DI Container

```python
# src/infrastructure/di/app_container.py
from dependency_injector import containers, providers
from core.config import Settings
from infrastructure.storage.minio_provider import MinIOStorageProvider
from infrastructure.storage.memory_provider import InMemoryStorageProvider

class Container(containers.DeclarativeContainer):
    config = providers.Configuration()

    storage_provider = providers.Selector(
        config.storage.provider,
        minio=providers.Singleton(
            MinIOStorageProvider,
            endpoint=config.storage.minio.endpoint,
            access_key=config.storage.minio.access_key,
            secret_key=config.storage.minio.secret_key,
            bucket=config.storage.minio.bucket,
        ),
        memory=providers.Singleton(InMemoryStorageProvider),
    )
```

### 5. Criar Dependency

```python
# src/interface/dependencies.py
from fastapi import Depends
from core.protocols.storage import StorageProvider

def get_storage_provider() -> StorageProvider:
    return container.storage_provider()
```

### 6. Usar no Endpoint

```python
# src/interface/v1/files.py
from fastapi import APIRouter, UploadFile, Depends
from core.protocols.storage import StorageProvider

router = APIRouter(prefix="/files", tags=["Files"])

@router.post("/upload")
async def upload_file(
    file: UploadFile,
    storage: StorageProvider = Depends(get_storage_provider),
) -> dict:
    content = await file.read()
    url = await storage.upload(
        key=f"uploads/{file.filename}",
        data=content,
        content_type=file.content_type or "application/octet-stream",
    )
    return {"url": url}
```

### 7. Testes

```python
# tests/unit/infrastructure/storage/test_memory_provider.py
import pytest
from infrastructure.storage.memory_provider import InMemoryStorageProvider

@pytest.fixture
def storage():
    return InMemoryStorageProvider()

@pytest.mark.asyncio
async def test_upload_and_download(storage):
    data = b"test content"
    await storage.upload("test.txt", data, "text/plain")

    downloaded = await storage.download("test.txt")
    assert downloaded == data

@pytest.mark.asyncio
async def test_delete(storage):
    await storage.upload("test.txt", b"content", "text/plain")
    assert await storage.exists("test.txt")

    await storage.delete("test.txt")
    assert not await storage.exists("test.txt")
```

## Outros Exemplos de Integrações

### Cache Provider

```python
# Protocol: src/core/protocols/cache.py
class CacheProvider[T](Protocol):
    async def get(self, key: str) -> T | None: ...
    async def set(self, key: str, value: T, ttl: int | None = None) -> None: ...
    async def delete(self, key: str) -> bool: ...

# Implementations:
# - src/infrastructure/cache/redis_provider.py
# - src/infrastructure/cache/memory_provider.py
```

### Messaging Provider

```python
# Protocol: src/core/protocols/messaging.py
class MessagePublisher(Protocol):
    async def publish(self, topic: str, message: dict) -> None: ...

class MessageConsumer(Protocol):
    async def subscribe(self, topic: str, handler: Callable) -> None: ...

# Implementations:
# - src/infrastructure/kafka/producer.py
# - src/infrastructure/tasks/rabbitmq_queue.py
```

### Search Provider

```python
# Protocol: src/core/protocols/search.py
class SearchProvider[T](Protocol):
    async def index(self, id: str, document: T) -> None: ...
    async def search(self, query: str, limit: int = 10) -> list[T]: ...
    async def delete(self, id: str) -> bool: ...

# Implementation:
# - src/infrastructure/elasticsearch/repository.py
```

## Checklist

- [ ] Protocol definido em `src/core/protocols/`
- [ ] Provider de produção implementado
- [ ] Provider de teste (in-memory) implementado
- [ ] Registrado no DI Container
- [ ] Dependency criada para FastAPI
- [ ] Configuração adicionada em Settings
- [ ] Testes unitários escritos
- [ ] Documentação atualizada
