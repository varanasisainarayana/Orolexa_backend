#config.py
import os
from pydantic_settings import BaseSettings
from typing import Optional, List
from functools import lru_cache

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Dental AI API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    
    # Server Settings (Railway specific)
    HOST: str = "0.0.0.0"
    PORT: int = int(os.environ.get("PORT", 8000))  # Railway sets PORT
    WORKERS: int = 1  # Railway works better with single worker
    
    # Database Settings (Railway specific)
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./app/orolexa.db")
    
    # Security Settings
    SECRET_KEY: str = os.environ.get("JWT_SECRET_KEY", "your-secret-key-change-in-production")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # CORS Settings (Railway specific)
    ALLOWED_ORIGINS: List[str] = ["*"]  # Update with your frontend domain
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: List[str] = ["*"]
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    UPLOAD_DIR: str = "uploads"
    THUMBNAIL_SIZE: tuple = (150, 150)
    
    # AI Settings
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GEMINI_MODEL: str = "gemini-1.5-flash"
    
    # Twilio Settings
    TWILIO_ACCOUNT_SID: str = os.environ.get("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.environ.get("TWILIO_AUTH_TOKEN", "")
    TWILIO_VERIFY_SERVICE_SID: str = os.environ.get("TWILIO_VERIFY_SERVICE_SID", "")
    
    # Logging Settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # Health Check
    HEALTH_CHECK_ENABLED: bool = True
    
    # Base URL for image serving (Railway specific)
    BASE_URL: str = os.environ.get("BASE_URL", "http://localhost:8000")
    
    # Railway specific settings
    RAILWAY_ENVIRONMENT: bool = os.environ.get("RAILWAY_ENVIRONMENT", "false").lower() == "true"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Create settings instance
settings = get_settings()
