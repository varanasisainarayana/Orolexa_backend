import google.generativeai as genai
from ...config import settings
from ...application.ports.ai_provider import AIProvider


class GeminiProvider(AIProvider):
    def __init__(self) -> None:
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    def generate_text(self, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        result = self.model.generate_content([
            prompt,
            {"mime_type": mime_type, "data": image_bytes},
        ])
        return getattr(result, "text", str(result))


