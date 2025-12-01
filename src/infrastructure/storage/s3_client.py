"""S3 storage client."""
import logging
from dataclasses import dataclass
from typing import BinaryIO

logger = logging.getLogger(__name__)

@dataclass
class S3Config:
    bucket: str
    region: str = "us-east-1"
    endpoint_url: str | None = None

class S3Client:
    def __init__(self, config: S3Config) -> None:
        self._config = config
        self._client = None
    
    async def upload(self, key: str, data: bytes | BinaryIO, content_type: str = "application/octet-stream") -> str:
        logger.info(f"Uploading to s3://{self._config.bucket}/{key}")
        return f"s3://{self._config.bucket}/{key}"
    
    async def download(self, key: str) -> bytes:
        logger.info(f"Downloading s3://{self._config.bucket}/{key}")
        return b""
    
    async def delete(self, key: str) -> bool:
        logger.info(f"Deleting s3://{self._config.bucket}/{key}")
        return True
    
    async def exists(self, key: str) -> bool:
        return False
    
    def get_url(self, key: str, expires_in: int = 3600) -> str:
        return f"https://{self._config.bucket}.s3.{self._config.region}.amazonaws.com/{key}"
