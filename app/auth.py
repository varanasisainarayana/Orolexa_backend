# app/auth.py
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel import Session, select
from .database import engine
from .models import User, OTPCode, UserSession
from .schemas import (
    LoginRequest, LoginResponse, RegisterRequest, RegisterResponse,
    VerifyOTPRequest, VerifyOTPResponse, ResendOTPRequest, ResendOTPResponse,
    UserResponse, AuthResponse, ErrorResponse
)
from .utils import create_jwt_token, create_refresh_token, decode_jwt_token
from twilio.rest import Client
from twilio.http.http_client import TwilioHttpClient
import os
import uuid
import shutil
import base64
from datetime import datetime, timedelta
import traceback
from .config import settings
import logging
import json
from PIL import Image
import io

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Twilio config with timeout
_twilio_http_client = TwilioHttpClient(timeout=10)
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN, http_client=_twilio_http_client)

def generate_otp() -> str:
    """Generate a 6-digit OTP"""
    import random
    return str(random.randint(100000, 999999))

def save_profile_image(base64_image: str, user_id: str) -> str:
    """Save base64 profile image and return URL"""
    try:
        # Extract base64 data
        header, data = base64_image.split(',', 1)
        image_data = base64.b64decode(data)
        
        # Create uploads directory
        uploads_dir = f"{settings.UPLOAD_DIR}/profiles"
        os.makedirs(uploads_dir, exist_ok=True)
        
        # Generate filename
        filename = f"{user_id}.jpg"
        file_path = os.path.join(uploads_dir, filename)
        
        # Save image
        with open(file_path, "wb") as f:
            f.write(image_data)
        
        return file_path
    except Exception as e:
        logger.error(f"Error saving profile image: {e}")
        raise HTTPException(status_code=500, detail="Failed to save profile image")

def cleanup_expired_otps():
    """Clean up expired OTP codes"""
    try:
        with Session(engine) as session:
            expired_otps = session.exec(
                select(OTPCode).where(OTPCode.expires_at < datetime.utcnow())
            ).all()
            
            for otp in expired_otps:
                session.delete(otp)
            session.commit()
    except Exception as e:
        logger.error(f"Error cleaning up expired OTPs: {e}")

def check_rate_limit(phone: str, flow: str) -> bool:
    """Check if user has exceeded rate limit for OTP requests"""
    try:
        with Session(engine) as session:
            # Count OTP requests in the last hour
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            recent_otps = session.exec(
                select(OTPCode)
                .where(OTPCode.phone == phone)
                .where(OTPCode.flow == flow)
                .where(OTPCode.created_at > one_hour_ago)
            ).all()
            
            return len(recent_otps) < 3  # Max 3 requests per hour
    except Exception as e:
        logger.error(f"Error checking rate limit: {e}")
        return True  # Allow if error

@router.post("/login", response_model=LoginResponse)
async def login(payload: LoginRequest):
    """
    Login API - Send OTP for existing users
    """
    # Quick env guard
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_VERIFY_SERVICE_SID):
        raise HTTPException(status_code=500, detail="SMS service not configured")
    
    try:
        # Check if user exists
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.phone == payload.phone)
            ).first()
            
            if not user:
                return LoginResponse(
                    success=False,
                    message="Invalid phone number",
                    data={"error": "PHONE_NOT_FOUND"}
                )
        
        # Check rate limit
        if not check_rate_limit(payload.phone, "login"):
            return LoginResponse(
                success=False,
                message="Too many OTP requests. Please try again later.",
                data={"error": "RATE_LIMIT_EXCEEDED"}
            )
        
        # Generate OTP
        otp = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Save OTP to database
        with Session(engine) as session:
            otp_code = OTPCode(
                phone=payload.phone,
                otp=otp,
                flow="login",
                expires_at=expires_at
            )
            session.add(otp_code)
            session.commit()
        
        # Send OTP via Twilio (in production, use Twilio Verify)
        try:
            if settings.DEBUG:
                logger.info(f"DEBUG: OTP for {payload.phone}: {otp}")
            else:
                verification = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
                    to=payload.phone, channel="sms"
                )
        except Exception as e:
            logger.error(f"Twilio error: {e}")
            # In production, you might want to handle this differently
            if not settings.DEBUG:
                raise HTTPException(status_code=500, detail="Failed to send OTP")
        
        return LoginResponse(
            success=True,
            message="OTP sent successfully",
            data={
                "phone": payload.phone,
                "otp_expires_in": 300  # 5 minutes
            }
        )
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register(payload: RegisterRequest):
    """
    Register API - Create new user and send OTP
    """
    # Quick env guard
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_VERIFY_SERVICE_SID):
        raise HTTPException(status_code=500, detail="SMS service not configured")
    
    try:
        # Check if user already exists
        with Session(engine) as session:
            existing_user = session.exec(
                select(User).where(User.phone == payload.phone)
            ).first()
            
            if existing_user:
                return RegisterResponse(
                    success=False,
                    message="Phone number already registered",
                    data={"error": "PHONE_ALREADY_EXISTS"}
                )
        
        # Check rate limit
        if not check_rate_limit(payload.phone, "register"):
            return RegisterResponse(
                success=False,
                message="Too many OTP requests. Please try again later.",
                data={"error": "RATE_LIMIT_EXCEEDED"}
            )
        
        # Generate user ID
        user_id = str(uuid.uuid4())
        
        # Save profile image if provided
        profile_image_url = None
        if payload.profile_image:
            profile_image_url = save_profile_image(payload.profile_image, user_id)
        
        # Generate OTP
        otp = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Save OTP and user data to database
        with Session(engine) as session:
            otp_code = OTPCode(
                phone=payload.phone,
                otp=otp,
                flow="register",
                expires_at=expires_at
            )
            session.add(otp_code)
            
            # Create user (will be activated after OTP verification)
            user = User(
                id=user_id,
                name=payload.name,
                phone=payload.phone,
                country_code=payload.country_code,
                age=payload.age,
                date_of_birth=datetime.strptime(payload.date_of_birth, '%Y-%m-%d') if payload.date_of_birth else None,
                profile_image_url=profile_image_url,
                is_verified=False
            )
            session.add(user)
            session.commit()
        
        # Send OTP via Twilio
        try:
            if settings.DEBUG:
                logger.info(f"DEBUG: OTP for {payload.phone}: {otp}")
            else:
                verification = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
                    to=payload.phone, channel="sms"
                )
        except Exception as e:
            logger.error(f"Twilio error: {e}")
            if not settings.DEBUG:
                raise HTTPException(status_code=500, detail="Failed to send OTP")
        
        return RegisterResponse(
            success=True,
            message="Registration successful. OTP sent for verification.",
            data={
                "user_id": user_id,
                "phone": payload.phone,
                "otp_expires_in": 300  # 5 minutes
            }
        )
        
    except Exception as e:
        logger.error(f"Register error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp(payload: VerifyOTPRequest):
    """
    OTP Verification API - Verify OTP for login or register
    """
    try:
        # Clean up expired OTPs
        cleanup_expired_otps()
        
        # Find valid OTP
        with Session(engine) as session:
            otp_code = session.exec(
                select(OTPCode)
                .where(OTPCode.phone == payload.phone)
                .where(OTPCode.otp == payload.otp)
                .where(OTPCode.flow == payload.flow)
                .where(OTPCode.is_used == False)
                .where(OTPCode.expires_at > datetime.utcnow())
            ).first()
            
            if not otp_code:
                return VerifyOTPResponse(
                    success=False,
                    message="Invalid OTP",
                    data={"error": "INVALID_OTP"}
                )
            
            # Mark OTP as used
            otp_code.is_used = True
            session.add(otp_code)
            
            if payload.flow == "login":
                # Login flow - get existing user
                user = session.exec(
                    select(User).where(User.phone == payload.phone)
                ).first()
                
                if not user:
                    return VerifyOTPResponse(
                        success=False,
                        message="User not found",
                        data={"error": "USER_NOT_FOUND"}
                    )
                
                # Mark user as verified
                user.is_verified = True
                session.add(user)
                
            elif payload.flow == "register":
                # Register flow - activate user
                user = session.exec(
                    select(User).where(User.phone == payload.phone)
                ).first()
                
                if not user:
                    return VerifyOTPResponse(
                        success=False,
                        message="User not found",
                        data={"error": "USER_NOT_FOUND"}
                    )
                
                # Mark user as verified
                user.is_verified = True
                session.add(user)
            
            # Generate tokens
            access_token = create_jwt_token({"sub": user.id})
            refresh_token = create_refresh_token({"sub": user.id})
            
            # Create user session
            session_record = UserSession(
                user_id=user.id,
                token=access_token,
                refresh_token=refresh_token,
                expires_at=datetime.utcnow() + timedelta(days=30)
            )
            session.add(session_record)
            
            session.commit()
            session.refresh(user)
        
        # Prepare user response
        user_response = UserResponse(
            id=user.id,
            name=user.name,
            phone=user.phone,
            age=user.age,
            profile_image_url=user.profile_image_url,
            date_of_birth=user.date_of_birth.strftime('%Y-%m-%d') if user.date_of_birth else None,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        
        return VerifyOTPResponse(
            success=True,
            message="OTP verified successfully",
            data={
                "user": user_response.dict(),
                "token": access_token,
                "refresh_token": refresh_token
            }
        )
        
    except Exception as e:
        logger.error(f"Verify OTP error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/resend-otp", response_model=ResendOTPResponse)
async def resend_otp(payload: ResendOTPRequest):
    """
    Resend OTP API
    """
    # Quick env guard
    if not (settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_VERIFY_SERVICE_SID):
        raise HTTPException(status_code=500, detail="SMS service not configured")
    
    try:
        # Check if user exists
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.phone == payload.phone)
            ).first()
            
            if not user:
                return ResendOTPResponse(
                    success=False,
                    message="Phone number not registered",
                    data={"error": "PHONE_NOT_FOUND"}
                )
        
        # Check rate limit
        if not check_rate_limit(payload.phone, "login"):
            return ResendOTPResponse(
                success=False,
                message="Too many OTP requests. Please try again later.",
                data={"error": "RATE_LIMIT_EXCEEDED"}
            )
        
        # Generate new OTP
        otp = generate_otp()
        expires_at = datetime.utcnow() + timedelta(minutes=5)
        
        # Save new OTP to database
        with Session(engine) as session:
            otp_code = OTPCode(
                phone=payload.phone,
                otp=otp,
                flow="login",
                expires_at=expires_at
            )
            session.add(otp_code)
            session.commit()
        
        # Send OTP via Twilio
        try:
            if settings.DEBUG:
                logger.info(f"DEBUG: Resend OTP for {payload.phone}: {otp}")
            else:
                verification = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
                    to=payload.phone, channel="sms"
                )
        except Exception as e:
            logger.error(f"Twilio error: {e}")
            if not settings.DEBUG:
                raise HTTPException(status_code=500, detail="Failed to send OTP")
        
        return ResendOTPResponse(
            success=True,
            message="OTP resent successfully",
            data={
                "otp_expires_in": 300  # 5 minutes
            }
        )
        
    except Exception as e:
        logger.error(f"Resend OTP error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Legacy endpoints for backward compatibility
@router.get("/ping")
def auth_ping():
    return {"ok": True, "twilio_configured": bool(settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_VERIFY_SERVICE_SID)}
