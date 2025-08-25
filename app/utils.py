import os
import jwt
import random
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
    """Create JWT token with expiration"""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    
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
