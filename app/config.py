"""Centralized configuration with sane production defaults."""
import os
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional, List
from functools import lru_cache

class Settings(BaseSettings):
    # Application Settings
    APP_NAME: str = "Dental AI API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    DOCS_ENABLED: bool = True  # Can disable in production
    
    # Server Settings (Railway specific)
    HOST: str = "0.0.0.0"
    PORT: int = int(os.environ.get("PORT", 8000))  # Railway sets PORT
    WORKERS: int = 1  # Railway works better with single worker
    
    # Database Settings (Railway specific)
    DATABASE_URL: str = os.environ.get("DATABASE_URL", "sqlite:///./app/orolexa.db")
    
    # Security Settings
    SECRET_KEY: str = Field(default="change-me-in-prod", alias="JWT_SECRET_KEY")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    
    # CORS Settings (Railway specific)
    # Comma-separated list in env (e.g., https://app.orolexa.com,https://orolexa.com)
    ALLOWED_ORIGINS: List[str] = ["*"]  # Update with your frontend domain
    ALLOWED_METHODS: List[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    ALLOWED_HEADERS: List[str] = ["*"]
    CORS_ALLOW_CREDENTIALS: bool = True
    
    # File Upload Settings
    MAX_FILE_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    UPLOAD_DIR: str = "uploads"
    THUMBNAIL_SIZE: tuple = (150, 150)
    # Middleware settings
    GZIP_MIN_SIZE: int = 500  # bytes
    
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
    
    # Railway specific settings (string to avoid boolean parsing errors)
    RAILWAY_ENVIRONMENT: str = os.environ.get("RAILWAY_ENVIRONMENT", "")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./orolexa.db")

# Security / CORS
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",")
TRUSTED_HOSTS = os.getenv("TRUSTED_HOSTS", "*").split(",")

# ESP32 limits
ESP32_MAX_IMAGE_SIZE = int(os.getenv("ESP32_MAX_IMAGE_SIZE", str(10 * 1024 * 1024)))  # 10MB
ESP32_MAX_IMAGES_PER_REQUEST = int(os.getenv("ESP32_MAX_IMAGES_PER_REQUEST", "10"))
ESP32_ANALYSIS_TIMEOUT_MS = int(os.getenv("ESP32_ANALYSIS_TIMEOUT", "30000"))
ESP32_STREAM_TIMEOUT_MS = int(os.getenv("ESP32_STREAM_TIMEOUT", "5000"))

# Rate limiting (simple in-memory)
RATE_LIMIT_WINDOW_SEC = int(os.getenv("RATE_LIMIT_WINDOW_SEC", "900"))  # 15 min
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("RATE_LIMIT_MAX_REQUESTS", "100"))

# App
ENV = os.getenv("ENV", "production")
DEBUG = ENV != "production"
