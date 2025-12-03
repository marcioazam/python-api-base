# MinIO/S3 Integration

## Overview

MinIO é usado para armazenamento de objetos, compatível com API S3.

## Configuration

```bash
MINIO__ENDPOINT=localhost:9000
MINIO__ACCESS_KEY=minioadmin
MINIO__SECRET_KEY=minioadmin
MINIO__BUCKET=uploads
MINIO__SECURE=false
```

## Client Setup

```python
from miniopy_async import Minio

class MinIOClient:
    def __init__(self, endpoint: str, access_key: str, secret_key: str, secure: bool = False):
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )
    
    async def ensure_bucket(self, bucket: str) -> None:
        if not await self._client.bucket_exists(bucket):
            await self._client.make_bucket(bucket)
```

## Upload Operations

```python
async def upload_file(
    self,
    bucket: str,
    object_name: str,
    data: bytes,
    content_type: str,
) -> str:
    """Upload file and return URL."""
    await self._client.put_object(
        bucket_name=bucket,
        object_name=object_name,
        data=io.BytesIO(data),
        length=len(data),
        content_type=content_type,
    )
    return f"/{bucket}/{object_name}"

async def upload_stream(
    self,
    bucket: str,
    object_name: str,
    stream: AsyncIterator[bytes],
    content_type: str,
) -> str:
    """Upload from stream."""
    # Collect chunks
    chunks = []
    async for chunk in stream:
        chunks.append(chunk)
    data = b"".join(chunks)
    
    return await self.upload_file(bucket, object_name, data, content_type)
```

## Download Operations

```python
async def download_file(self, bucket: str, object_name: str) -> bytes:
    """Download file content."""
    response = await self._client.get_object(bucket, object_name)
    return await response.read()

async def get_presigned_url(
    self,
    bucket: str,
    object_name: str,
    expires: int = 3600,
) -> str:
    """Generate presigned URL for download."""
    return await self._client.presigned_get_object(
        bucket,
        object_name,
        expires=timedelta(seconds=expires),
    )

async def get_presigned_upload_url(
    self,
    bucket: str,
    object_name: str,
    expires: int = 3600,
) -> str:
    """Generate presigned URL for upload."""
    return await self._client.presigned_put_object(
        bucket,
        object_name,
        expires=timedelta(seconds=expires),
    )
```

## File Management

```python
async def delete_file(self, bucket: str, object_name: str) -> bool:
    """Delete a file."""
    await self._client.remove_object(bucket, object_name)
    return True

async def list_files(self, bucket: str, prefix: str = "") -> list[ObjectInfo]:
    """List files in bucket."""
    objects = []
    async for obj in self._client.list_objects(bucket, prefix=prefix):
        objects.append(ObjectInfo(
            name=obj.object_name,
            size=obj.size,
            last_modified=obj.last_modified,
        ))
    return objects

async def file_exists(self, bucket: str, object_name: str) -> bool:
    """Check if file exists."""
    try:
        await self._client.stat_object(bucket, object_name)
        return True
    except Exception:
        return False
```

## File Upload Handler

```python
class FileUploadHandler:
    ALLOWED_TYPES = ["image/jpeg", "image/png", "application/pdf"]
    MAX_SIZE = 10 * 1024 * 1024  # 10MB
    
    def __init__(self, minio: MinIOClient, bucket: str):
        self._minio = minio
        self._bucket = bucket
    
    async def upload(self, file: UploadFile, folder: str = "uploads") -> FileInfo:
        # Validate
        if file.content_type not in self.ALLOWED_TYPES:
            raise ValidationError(f"Type not allowed: {file.content_type}")
        
        content = await file.read()
        if len(content) > self.MAX_SIZE:
            raise ValidationError(f"File too large: {len(content)} bytes")
        
        # Generate unique name
        ext = Path(file.filename).suffix
        unique_name = f"{uuid4().hex}{ext}"
        path = f"{folder}/{unique_name}"
        
        # Upload
        await self._minio.upload_file(self._bucket, path, content, file.content_type)
        url = await self._minio.get_presigned_url(self._bucket, path)
        
        return FileInfo(
            filename=file.filename,
            path=path,
            url=url,
            size=len(content),
            content_type=file.content_type,
        )
```

## Lifecycle Policies

```python
# Set lifecycle policy to delete old files
lifecycle_config = {
    "Rules": [
        {
            "ID": "delete-old-temp-files",
            "Status": "Enabled",
            "Filter": {"Prefix": "temp/"},
            "Expiration": {"Days": 7},
        }
    ]
}
```

## Best Practices

1. **Use presigned URLs** - For secure direct access
2. **Validate file types** - Whitelist allowed types
3. **Set size limits** - Prevent abuse
4. **Use unique names** - Prevent collisions
5. **Organize by folder** - Logical structure
