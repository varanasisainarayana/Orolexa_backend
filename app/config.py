"""Centralized configuration with sane production defaults."""
import os
from dotenv import load_dotenv

load_dotenv()

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
