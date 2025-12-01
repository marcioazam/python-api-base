"""Local file storage client."""
import logging
from pathlib import Path
from typing import BinaryIO

logger = logging.getLogger(__name__)

class LocalStorage:
    def __init__(self, base_path: str = "./storage") -> None:
        self._base_path = Path(base_path)
        self._base_path.mkdir(parents=True, exist_ok=True)
    
    async def upload(self, key: str, data: bytes | BinaryIO) -> str:
        path = self._base_path / key
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, bytes):
            path.write_bytes(data)
        else:
            path.write_bytes(data.read())
        logger.info(f"Saved to {path}")
        return str(path)
    
    async def download(self, key: str) -> bytes:
        path = self._base_path / key
        if not path.exists():
            raise FileNotFoundError(f"File not found: {key}")
        return path.read_bytes()
    
    async def delete(self, key: str) -> bool:
        path = self._base_path / key
        if path.exists():
            path.unlink()
            return True
        return False
    
    async def exists(self, key: str) -> bool:
        return (self._base_path / key).exists()
