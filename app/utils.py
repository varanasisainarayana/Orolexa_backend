import os
import jwt
import random
import uuid
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .config import settings

# Load environment variables
load_dotenv()

# JWT settings
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "supersecretkey")
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_MINUTES = int(os.getenv("JWT_EXPIRY_MINUTES", 60))

# =========================
# OTP Generation
# =========================
def generate_otp() -> str:
    """Generate a secure 6-digit OTP."""
    return str(random.randint(100000, 999999))


# =========================
# JWT Token Handling
# =========================
def create_jwt_token(data: dict):
    """Create JWT access token with expiration (24 hours)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)  # 24 hours
    to_encode.update({"exp": expire, "type": "access"})
    
    # Ensure SECRET_KEY is properly set
    if not settings.SECRET_KEY or settings.SECRET_KEY == "change-me-in-prod":
        raise ValueError("SECRET_KEY not properly configured")
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def create_refresh_token(data: dict):
    """Create JWT refresh token with expiration (30 days)"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=30)  # 30 days
    to_encode.update({"exp": expire, "type": "refresh"})
    
    # Ensure SECRET_KEY is properly set
    if not settings.SECRET_KEY or settings.SECRET_KEY == "change-me-in-prod":
        raise ValueError("SECRET_KEY not properly configured")
    
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

def decode_jwt_token(token: str):
    """Decode and verify JWT token"""
    try:
        # Ensure SECRET_KEY is properly set
        if not settings.SECRET_KEY or settings.SECRET_KEY == "change-me-in-prod":
            return None
            
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None

def verify_refresh_token(token: str):
    """Verify refresh token specifically"""
    try:
        payload = decode_jwt_token(token)
        if payload and payload.get("type") == "refresh":
            return payload
        return None
    except Exception:
        return None

def generate_session_id() -> str:
    """Generate a unique session ID"""
    return str(uuid.uuid4())
