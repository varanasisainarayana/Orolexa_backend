# app/production_config.py
"""
Production configuration settings for enhanced security and monitoring
"""

import os
from typing import List, Dict, Any
from pydantic import BaseSettings, Field

class ProductionSettings(BaseSettings):
    """Production-specific settings"""
    
    # Security Settings
    SECURITY_LEVEL: str = Field(default="high", description="Security level: low, medium, high")
    ENABLE_AUDIT_LOGGING: bool = Field(default=True, description="Enable audit logging")
    ENABLE_FRAUD_DETECTION: bool = Field(default=True, description="Enable fraud detection")
    REQUIRE_DEVICE_FINGERPRINT: bool = Field(default=True, description="Require device fingerprinting")
    
    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    MAX_REQUESTS_PER_HOUR: int = Field(default=3, description="Max requests per hour per phone")
    RATE_LIMIT_WINDOW_HOURS: int = Field(default=1, description="Rate limit window in hours")
    
    # OTP Settings
    OTP_EXPIRY_MINUTES: int = Field(default=10, description="OTP expiry time in minutes")
    MAX_OTP_ATTEMPTS: int = Field(default=5, description="Max OTP verification attempts")
    OTP_LENGTH: int = Field(default=6, description="OTP length")
    
    # Session Settings
    SESSION_EXPIRY_DAYS: int = Field(default=30, description="Session expiry in days")
    MAX_CONCURRENT_SESSIONS: int = Field(default=5, description="Max concurrent sessions per user")
    
    # Twilio Settings
    TWILIO_TIMEOUT_SECONDS: int = Field(default=15, description="Twilio request timeout")
    TWILIO_MAX_RETRIES: int = Field(default=3, description="Twilio max retries")
    TWILIO_ENABLE_LOGGING: bool = Field(default=True, description="Enable Twilio request logging")
    
    # Database Settings
    DB_CONNECTION_POOL_SIZE: int = Field(default=20, description="Database connection pool size")
    DB_MAX_OVERFLOW: int = Field(default=30, description="Database max overflow")
    DB_POOL_TIMEOUT: int = Field(default=30, description="Database pool timeout")
    
    # Logging Settings
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ENABLE_STRUCTURED_LOGGING: bool = Field(default=True, description="Enable structured logging")
    LOG_FILE_PATH: str = Field(default="/var/log/orolexa/app.log", description="Log file path")
    
    # Monitoring Settings
    ENABLE_METRICS: bool = Field(default=True, description="Enable metrics collection")
    METRICS_INTERVAL_SECONDS: int = Field(default=60, description="Metrics collection interval")
    ENABLE_HEALTH_CHECKS: bool = Field(default=True, description="Enable health checks")
    
    # CORS Settings (Production)
    ALLOWED_ORIGINS: List[str] = Field(default=[], description="Allowed CORS origins")
    ALLOWED_METHODS: List[str] = Field(default=["GET", "POST", "PUT", "DELETE", "OPTIONS"])
    ALLOWED_HEADERS: List[str] = Field(default=["*"])
    CORS_ALLOW_CREDENTIALS: bool = Field(default=True)
    
    # Cache Settings
    CACHE_ENABLED: bool = Field(default=True, description="Enable caching")
    CACHE_TTL_SECONDS: int = Field(default=300, description="Cache TTL in seconds")
    REDIS_URL: str = Field(default="", description="Redis URL for caching")
    
    # Backup Settings
    ENABLE_AUTO_BACKUP: bool = Field(default=True, description="Enable automatic backups")
    BACKUP_INTERVAL_HOURS: int = Field(default=24, description="Backup interval in hours")
    BACKUP_RETENTION_DAYS: int = Field(default=30, description="Backup retention in days")
    
    # Alerting Settings
    ENABLE_ALERTS: bool = Field(default=True, description="Enable alerting")
    ALERT_EMAIL: str = Field(default="", description="Alert email address")
    SLACK_WEBHOOK_URL: str = Field(default="", description="Slack webhook URL")
    
    # Performance Settings
    ENABLE_COMPRESSION: bool = Field(default=True, description="Enable response compression")
    ENABLE_CACHING: bool = Field(default=True, description="Enable response caching")
    MAX_REQUEST_SIZE: int = Field(default=10 * 1024 * 1024, description="Max request size in bytes")
    
    class Config:
        env_file = ".env"
        case_sensitive = True

# Production security configurations
PRODUCTION_SECURITY_CONFIG = {
    "low": {
        "max_otp_attempts": 10,
        "rate_limit_window": 2,
        "max_requests_per_window": 5,
        "session_expiry_days": 60,
        "require_device_fingerprint": False,
        "enable_fraud_detection": False
    },
    "medium": {
        "max_otp_attempts": 5,
        "rate_limit_window": 1,
        "max_requests_per_window": 3,
        "session_expiry_days": 30,
        "require_device_fingerprint": True,
        "enable_fraud_detection": True
    },
    "high": {
        "max_otp_attempts": 3,
        "rate_limit_window": 1,
        "max_requests_per_window": 2,
        "session_expiry_days": 7,
        "require_device_fingerprint": True,
        "enable_fraud_detection": True
    }
}

# Production monitoring thresholds
MONITORING_THRESHOLDS = {
    "error_rate_threshold": 0.05,  # 5% error rate
    "response_time_threshold": 2000,  # 2 seconds
    "memory_usage_threshold": 0.8,  # 80% memory usage
    "cpu_usage_threshold": 0.7,  # 70% CPU usage
    "database_connection_threshold": 0.8,  # 80% connection pool usage
}

# Production logging configuration
LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S"
        },
        "json": {
            "class": "pythonjsonlogger.jsonlogger.JsonFormatter",
            "format": "%(timestamp)s %(level)s %(name)s %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "structured",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "json",
            "filename": "/var/log/orolexa/app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "json",
            "filename": "/var/log/orolexa/error.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5
        }
    },
    "loggers": {
        "": {
            "level": "INFO",
            "handlers": ["console", "file", "error_file"],
            "propagate": False
        },
        "app.auth": {
            "level": "INFO",
            "handlers": ["console", "file", "error_file"],
            "propagate": False
        },
        "twilio": {
            "level": "WARNING",
            "handlers": ["console", "file"],
            "propagate": False
        }
    }
}

# Production environment variables
PRODUCTION_ENV_VARS = {
    "PYTHONPATH": "/app",
    "PYTHONUNBUFFERED": "1",
    "PYTHONDONTWRITEBYTECODE": "1",
    "TZ": "UTC",
    "LANG": "C.UTF-8",
    "LC_ALL": "C.UTF-8"
}

# Production dependencies
PRODUCTION_DEPENDENCIES = [
    "fastapi[all]>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlmodel>=0.0.8",
    "twilio>=8.10.0",
    "python-multipart>=0.0.6",
    "python-jose[cryptography]>=3.3.0",
    "passlib[bcrypt]>=1.7.4",
    "python-json-logger>=2.0.7",
    "redis>=5.0.0",
    "prometheus-client>=0.19.0",
    "structlog>=23.2.0",
    "sentry-sdk[fastapi]>=1.38.0"
]

# Production health check endpoints
HEALTH_CHECK_ENDPOINTS = [
    "/api/auth/health",
    "/api/auth/metrics",
    "/docs",
    "/openapi.json"
]

# Production security headers
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "X-XSS-Protection": "1; mode=block",
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "Referrer-Policy": "strict-origin-when-cross-origin",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'"
}

# Production rate limiting rules
RATE_LIMITING_RULES = {
    "login": {
        "max_requests": 3,
        "window_hours": 1,
        "block_duration_hours": 24
    },
    "register": {
        "max_requests": 2,
        "window_hours": 1,
        "block_duration_hours": 24
    },
    "verify_otp": {
        "max_requests": 5,
        "window_hours": 1,
        "block_duration_hours": 6
    },
    "resend_otp": {
        "max_requests": 2,
        "window_hours": 1,
        "block_duration_hours": 12
    }
}

# Production backup configuration
BACKUP_CONFIG = {
    "enabled": True,
    "schedule": "0 2 * * *",  # Daily at 2 AM
    "retention_days": 30,
    "compression": True,
    "encryption": True,
    "storage": {
        "type": "s3",  # or "local", "gcs"
        "bucket": "orolexa-backups",
        "region": "us-east-1"
    }
}

# Production alerting configuration
ALERTING_CONFIG = {
    "enabled": True,
    "channels": {
        "email": {
            "enabled": True,
            "recipients": ["admin@orolexa.com"],
            "smtp_server": "smtp.gmail.com",
            "smtp_port": 587
        },
        "slack": {
            "enabled": True,
            "webhook_url": "https://hooks.slack.com/services/...",
            "channel": "#alerts"
        }
    },
    "rules": {
        "high_error_rate": {
            "threshold": 0.05,
            "window_minutes": 5,
            "cooldown_minutes": 30
        },
        "high_response_time": {
            "threshold": 2000,
            "window_minutes": 5,
            "cooldown_minutes": 30
        },
        "service_down": {
            "threshold": 1,
            "window_minutes": 1,
            "cooldown_minutes": 5
        }
    }
}
