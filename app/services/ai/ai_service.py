# app/services/ai_service.py
import google.generativeai as genai
from typing import Optional
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

class AIService:
    def __init__(self):
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not configured")
            return
        
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
        except Exception as e:
            logger.error(f"Error initializing Gemini AI: {e}")
            self.model = None

    def generate_text(self, prompt: str, image_bytes: bytes, mime_type: str) -> Optional[str]:
        """Generate text analysis from image using Gemini AI"""
        if not self.model:
            logger.error("AI model not initialized")
            return None
        
        try:
            result = self.model.generate_content([
                prompt,
                {"mime_type": mime_type, "data": image_bytes},
            ])
            return getattr(result, "text", str(result))
        except Exception as e:
            logger.error(f"Error generating AI analysis: {e}")
            return None

    def analyze_dental_image(self, image_bytes: bytes, mime_type: str) -> Optional[str]:
        """Analyze dental image and provide health insights"""
        prompt = """
        Analyze this dental image and provide a comprehensive health assessment including:
        1. Overall oral health condition
        2. Specific issues or concerns identified
        3. Recommendations for improvement
        4. Urgency level (low, medium, high)
        5. Suggested next steps
        
        Please provide a detailed, professional analysis suitable for a dental health app.
        """
        
        return self.generate_text(prompt, image_bytes, mime_type)
