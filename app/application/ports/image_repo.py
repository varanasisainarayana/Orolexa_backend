from typing import Optional
from dataclasses import dataclass


@dataclass
class StoredImage:
    id: str
    content_type: str
    file_size: int


class ImageRepository:
    def save_bytes(self, user_id: str, data: bytes, filename: str, content_type: str, image_type: str = "profile") -> str:
        ...

    def save_base64(self, user_id: str, base64_data: str, image_type: str = "profile") -> str:
        ...

    def get_bytes(self, image_id: str) -> Optional[bytes]:
        ...

    def delete(self, image_id: str) -> bool:
        ...


