from typing import Protocol


class StorageRepository(Protocol):
    def save_bytes(self, subdir: str, filename: str, data: bytes) -> str:
        ...


