import os
from datetime import datetime

from ...config import settings
from ...application.ports.storage_repo import StorageRepository


class LocalStorageRepository(StorageRepository):
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


