import os
from datetime import datetime
from typing import Optional
from .config import settings


class StorageService:
    """Local filesystem storage. Saves files under settings.UPLOAD_DIR."""

    def __init__(self) -> None:
        self.upload_dir = settings.UPLOAD_DIR

    def save_bytes(self, subdir: str, filename: str, data: bytes) -> str:
        timestamped = f"{int(datetime.utcnow().timestamp()*1000)}_{filename}"
        dest_dir = os.path.join(self.upload_dir, subdir) if subdir else self.upload_dir
        os.makedirs(dest_dir, exist_ok=True)
        path = os.path.join(dest_dir, timestamped)
        with open(path, "wb") as f:
            f.write(data)
        return path

    def save_uploadfile(self, subdir: str, upload_file) -> str:
        contents = upload_file.file.read()
        return self.save_bytes(subdir, upload_file.filename, contents)


_storage_instance: Optional[StorageService] = None

def get_storage() -> StorageService:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = StorageService()
    return _storage_instance
