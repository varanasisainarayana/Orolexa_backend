from typing import Protocol


class AIProvider(Protocol):
    def generate_text(self, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        ...


