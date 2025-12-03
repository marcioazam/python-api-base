# Storage Infrastructure

## Overview

O sistema utiliza MinIO/S3 para armazenamento de objetos com abstração via interface.

## Storage Protocol

```python
class FileStorage(Protocol):
    async def upload(self, path: str, content: bytes, content_type: str) -> str: ...
    async def download(self, path: str) -> bytes: ...
    async def delete(self, path: str) -> bool: ...
    async def exists(self, path: str) -> bool: ...
    async def get_url(self, path: str, expires: int = 3600) -> str: ...
```

## MinIO Provider

```python
from miniopy_async import Minio

class MinIOStorageProvider(FileStorage):
    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key)
        self._bucket = bucket
    
    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        await self._client.put_object(
            bucket_name=self._bucket,
            object_name=path,
            data=io.BytesIO(content),
            length=len(content),
            content_type=content_type,
        )
        return f"/{self._bucket}/{path}"
    
    async def download(self, path: str) -> bytes:
        response = await self._client.get_object(self._bucket, path)
        return await response.read()
    
    async def delete(self, path: str) -> bool:
        await self._client.remove_object(self._bucket, path)
        return True
    
    async def get_url(self, path: str, expires: int = 3600) -> str:
        return await self._client.presigned_get_object(
            self._bucket,
            path,
            expires=timedelta(seconds=expires),
        )
```

## Memory Provider (Testing)

```python
class InMemoryStorageProvider(FileStorage):
    def __init__(self):
        self._storage: dict[str, tuple[bytes, str]] = {}
    
    async def upload(self, path: str, content: bytes, content_type: str) -> str:
        self._storage[path] = (content, content_type)
        return f"/memory/{path}"
    
    async def download(self, path: str) -> bytes:
        if path not in self._storage:
            raise FileNotFoundError(path)
        return self._storage[path][0]
    
    async def delete(self, path: str) -> bool:
        if path in self._storage:
            del self._storage[path]
            return True
        return False
```

## File Upload Handler

```python
@dataclass
class FileInfo:
    filename: str
    content_type: str
    size: int
    path: str
    url: str

class FileUploadHandler:
    ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"]
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, storage: FileStorage):
        self._storage = storage
    
    async def upload(self, file: UploadFile, folder: str = "uploads") -> FileInfo:
        # Validate
        if file.content_type not in self.ALLOWED_TYPES:
            raise ValidationError(f"File type not allowed: {file.content_type}")
        
        content = await file.read()
        if len(content) > self.MAX_SIZE:
            raise ValidationError(f"File too large: {len(content)} bytes")
        
        # Generate path
        ext = Path(file.filename).suffix
        unique_name = f"{uuid4().hex}{ext}"
        path = f"{folder}/{unique_name}"
        
        # Upload
        await self._storage.upload(path, content, file.content_type)
        url = await self._storage.get_url(path)
        
        return FileInfo(
            filename=file.filename,
            content_type=file.content_type,
            size=len(content),
            path=path,
            url=url,
        )
```

## Usage in Router

```python
@router.post("/upload")
async def upload_file(
    file: UploadFile,
    handler: FileUploadHandler = Depends(get_file_handler),
) -> FileInfo:
    return await handler.upload(file)

@router.get("/files/{path:path}")
async def get_file_url(
    path: str,
    storage: FileStorage = Depends(get_storage),
) -> dict:
    url = await storage.get_url(path)
    return {"url": url}
```

## Best Practices

1. **Validate file types** - Whitelist allowed types
2. **Limit file sizes** - Prevent abuse
3. **Use presigned URLs** - For secure access
4. **Generate unique names** - Prevent collisions
5. **Organize by folder** - Use logical structure
