# app/auth_production.py
"""
Production-ready authentication module with enhanced security, monitoring, and error handling
"""

from fastapi import APIRouter, HTTPException, Depends, Request, BackgroundTasks
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
from twilio.base.exceptions import TwilioException, TwilioRestException
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
import re
import hashlib
import secrets
from typing import Optional, Dict, Any
import asyncio
from contextlib import asynccontextmanager
import time
from dataclasses import dataclass
from enum import Enum

# Enhanced logging configuration
logger = logging.getLogger(__name__)

# Production constants
MAX_OTP_ATTEMPTS = 5
OTP_EXPIRY_MINUTES = 10
RATE_LIMIT_WINDOW_HOURS = 1
MAX_REQUESTS_PER_WINDOW = 3
SESSION_EXPIRY_DAYS = 30
PASSWORD_MIN_LENGTH = 8

class SecurityLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

@dataclass
class SecurityConfig:
    """Security configuration for production"""
    max_otp_attempts: int = MAX_OTP_ATTEMPTS
    otp_expiry_minutes: int = OTP_EXPIRY_MINUTES
    rate_limit_window_hours: int = RATE_LIMIT_WINDOW_HOURS
    max_requests_per_window: int = MAX_REQUESTS_PER_WINDOW
    session_expiry_days: int = SESSION_EXPIRY_DAYS
    require_device_fingerprint: bool = True
    enable_audit_logging: bool = True
    enable_fraud_detection: bool = True

# Production security configuration
security_config = SecurityConfig()

router = APIRouter(prefix="/api/auth", tags=["Authentication"])

# Enhanced Twilio config with retry logic and timeout
_twilio_http_client = TwilioHttpClient(
    timeout=15,  # Increased timeout for production
    max_retries=3  # Retry failed requests
)

# Initialize Twilio client with error handling
try:
    client = Client(
        settings.TWILIO_ACCOUNT_SID, 
        settings.TWILIO_AUTH_TOKEN, 
        http_client=_twilio_http_client
    )
    logger.info("Twilio client initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize Twilio client: {e}")
    client = None

# In-memory cache for rate limiting (use Redis in production)
_rate_limit_cache: Dict[str, Dict[str, Any]] = {}

def extract_country_code(phone: str) -> str:
    """Extract country code from phone number with enhanced validation"""
    try:
        # Remove any non-digit characters except +
        phone_clean = re.sub(r'[^\d+]', '', phone)
        
        # Validate phone number format
        if not re.match(r'^\+\d{1,4}\d{6,14}$', phone_clean):
            raise ValueError(f"Invalid phone number format: {phone}")
        
        # Enhanced country code patterns with validation
        country_patterns = {
            '+1': ['US', 'Canada'],
            '+44': ['UK'],
            '+91': ['India'],
            '+86': ['China'],
            '+81': ['Japan'],
            '+49': ['Germany'],
            '+33': ['France'],
            '+39': ['Italy'],
            '+34': ['Spain'],
            '+7': ['Russia'],
            '+55': ['Brazil'],
            '+52': ['Mexico'],
            '+61': ['Australia'],
            '+82': ['South Korea'],
            '+31': ['Netherlands'],
            '+46': ['Sweden'],
            '+47': ['Norway'],
            '+45': ['Denmark'],
            '+358': ['Finland'],
            '+48': ['Poland'],
            '+420': ['Czech Republic'],
            '+36': ['Hungary'],
            '+380': ['Ukraine'],
            '+351': ['Portugal'],
            '+30': ['Greece'],
            '+90': ['Turkey'],
            '+971': ['UAE'],
            '+966': ['Saudi Arabia'],
            '+20': ['Egypt'],
            '+27': ['South Africa'],
            '+234': ['Nigeria'],
            '+254': ['Kenya'],
            '+256': ['Uganda'],
            '+233': ['Ghana'],
            '+225': ['Ivory Coast'],
            '+237': ['Cameroon'],
            '+212': ['Morocco'],
            '+216': ['Tunisia'],
            '+213': ['Algeria'],
            '+218': ['Libya'],
            '+249': ['Sudan'],
            '+251': ['Ethiopia'],
            '+255': ['Tanzania'],
            '+260': ['Zambia'],
            '+263': ['Zimbabwe'],
            '+267': ['Botswana'],
            '+268': ['Swaziland'],
            '+269': ['Comoros'],
            '+290': ['Saint Helena'],
            '+291': ['Eritrea'],
            '+297': ['Aruba'],
            '+298': ['Faroe Islands'],
            '+299': ['Greenland'],
            '+350': ['Gibraltar'],
            '+352': ['Luxembourg'],
            '+353': ['Ireland'],
            '+354': ['Iceland'],
            '+355': ['Albania'],
            '+356': ['Malta'],
            '+357': ['Cyprus'],
            '+359': ['Bulgaria'],
            '+370': ['Lithuania'],
            '+371': ['Latvia'],
            '+372': ['Estonia'],
            '+373': ['Moldova'],
            '+374': ['Armenia'],
            '+375': ['Belarus'],
            '+376': ['Andorra'],
            '+377': ['Monaco'],
            '+378': ['San Marino'],
            '+379': ['Vatican'],
            '+381': ['Serbia'],
            '+382': ['Montenegro'],
            '+383': ['Kosovo'],
            '+385': ['Croatia'],
            '+386': ['Slovenia'],
            '+387': ['Bosnia and Herzegovina'],
            '+389': ['North Macedonia'],
            '+40': ['Romania'],
            '+41': ['Switzerland'],
            '+43': ['Austria'],
            '+50': ['Rwanda'],
            '+51': ['Peru'],
            '+53': ['Cuba'],
            '+54': ['Argentina'],
            '+56': ['Chile'],
            '+57': ['Colombia'],
            '+58': ['Venezuela'],
            '+590': ['Guadeloupe'],
            '+591': ['Bolivia'],
            '+592': ['Guyana'],
            '+593': ['Ecuador'],
            '+594': ['French Guiana'],
            '+595': ['Paraguay'],
            '+596': ['Martinique'],
            '+597': ['Suriname'],
            '+598': ['Uruguay'],
            '+599': ['Netherlands Antilles'],
            '+60': ['Malaysia'],
            '+62': ['Indonesia'],
            '+63': ['Philippines'],
            '+64': ['New Zealand'],
            '+65': ['Singapore'],
            '+66': ['Thailand'],
            '+670': ['East Timor'],
            '+672': ['Australia'],
            '+673': ['Brunei'],
            '+674': ['Nauru'],
            '+675': ['Papua New Guinea'],
            '+676': ['Tonga'],
            '+677': ['Solomon Islands'],
            '+678': ['Vanuatu'],
            '+679': ['Fiji'],
            '+680': ['Palau'],
            '+681': ['Wallis and Futuna'],
            '+682': ['Cook Islands'],
            '+683': ['Niue'],
            '+685': ['Samoa'],
            '+686': ['Kiribati'],
            '+687': ['New Caledonia'],
            '+688': ['Tuvalu'],
            '+689': ['French Polynesia'],
            '+690': ['Tokelau'],
            '+691': ['Micronesia'],
            '+692': ['Marshall Islands'],
            '+800': ['International Freephone'],
            '+808': ['International Shared Cost Service'],
            '+84': ['Vietnam'],
            '+850': ['North Korea'],
            '+852': ['Hong Kong'],
            '+853': ['Macau'],
            '+855': ['Cambodia'],
            '+856': ['Laos'],
            '+870': ['Inmarsat'],
            '+871': ['Inmarsat'],
            '+872': ['Inmarsat'],
            '+873': ['Inmarsat'],
            '+874': ['Inmarsat'],
            '+880': ['Bangladesh'],
            '+881': ['Global Mobile Satellite System'],
            '+882': ['International Networks'],
            '+883': ['International Networks'],
            '+886': ['Taiwan'],
            '+93': ['Afghanistan'],
            '+94': ['Sri Lanka'],
            '+95': ['Myanmar'],
            '+960': ['Maldives'],
            '+961': ['Lebanon'],
            '+962': ['Jordan'],
            '+963': ['Syria'],
            '+964': ['Iraq'],
            '+965': ['Kuwait'],
            '+967': ['Yemen'],
            '+968': ['Oman'],
            '+970': ['Palestine'],
            '+972': ['Israel'],
            '+973': ['Bahrain'],
            '+974': ['Qatar'],
            '+975': ['Bhutan'],
            '+976': ['Mongolia'],
            '+977': ['Nepal'],
            '+98': ['Iran'],
            '+992': ['Tajikistan'],
            '+993': ['Turkmenistan'],
            '+994': ['Azerbaijan'],
            '+995': ['Georgia'],
            '+996': ['Kyrgyzstan'],
            '+998': ['Uzbekistan'],
            '+999': ['Reserved']
        }
        
        # Find matching country code
        for code, countries in country_patterns.items():
            if phone_clean.startswith(code):
                logger.debug(f"Extracted country code {code} for {countries[0]} from {phone}")
                return code
        
        # Fallback: extract first 1-4 digits after +
        match = re.match(r'^\+(\d{1,4})', phone_clean)
        if match:
            extracted_code = '+' + match.group(1)
            logger.warning(f"Using fallback country code extraction: {extracted_code} for {phone}")
            return extracted_code
        else:
            logger.warning(f"Could not extract country code from {phone}, using default +1")
            return '+1'
            
    except Exception as e:
        logger.error(f"Error extracting country code from {phone}: {e}")
        return '+1'  # Default fallback

def generate_secure_otp() -> str:
    """Generate a cryptographically secure OTP"""
    return str(secrets.randbelow(1000000)).zfill(6)

def hash_phone_number(phone: str) -> str:
    """Hash phone number for security (one-way hash)"""
    return hashlib.sha256(phone.encode()).hexdigest()

def check_rate_limit(phone: str, flow: str, request_id: str) -> bool:
    """Enhanced rate limiting with request tracking"""
    try:
        current_time = time.time()
        window_start = current_time - (security_config.rate_limit_window_hours * 3600)
        
        # Clean old entries
        _rate_limit_cache = {k: v for k, v in _rate_limit_cache.items() 
                           if v['timestamp'] > window_start}
        
        cache_key = f"{phone}:{flow}"
        
        if cache_key not in _rate_limit_cache:
            _rate_limit_cache[cache_key] = {
                'count': 1,
                'timestamp': current_time,
                'requests': [{'id': request_id, 'time': current_time}]
            }
            return True
        
        entry = _rate_limit_cache[cache_key]
        
        # Remove old requests from this window
        entry['requests'] = [req for req in entry['requests'] 
                           if req['time'] > window_start]
        
        if len(entry['requests']) >= security_config.max_requests_per_window:
            logger.warning(f"Rate limit exceeded for {phone} in {flow} flow")
            return False
        
        entry['requests'].append({'id': request_id, 'time': current_time})
        entry['count'] = len(entry['requests'])
        
        return True
        
    except Exception as e:
        logger.error(f"Error in rate limiting: {e}")
        return True  # Allow if error

def audit_log(action: str, phone: str, user_id: Optional[str] = None, 
              request_id: str = None, ip_address: str = None, 
              success: bool = True, details: Dict[str, Any] = None):
    """Production audit logging"""
    if not security_config.enable_audit_logging:
        return
    
    audit_entry = {
        'timestamp': datetime.utcnow().isoformat(),
        'action': action,
        'phone_hash': hash_phone_number(phone),
        'user_id': user_id,
        'request_id': request_id,
        'ip_address': ip_address,
        'success': success,
        'details': details or {},
        'security_level': security_config.require_device_fingerprint
    }
    
    logger.info(f"AUDIT: {json.dumps(audit_entry)}")

def detect_fraud(phone: str, ip_address: str, user_agent: str) -> Dict[str, Any]:
    """Basic fraud detection"""
    if not security_config.enable_fraud_detection:
        return {'risk_level': 'low', 'flags': []}
    
    flags = []
    risk_level = 'low'
    
    # Check for suspicious patterns
    if not user_agent or user_agent.strip() == '':
        flags.append('missing_user_agent')
        risk_level = 'medium'
    
    if not ip_address or ip_address.strip() == '':
        flags.append('missing_ip_address')
        risk_level = 'medium'
    
    # Add more fraud detection logic here
    # - Check for known malicious IPs
    # - Check for unusual request patterns
    # - Check for geographic anomalies
    
    return {
        'risk_level': risk_level,
        'flags': flags,
        'phone': phone,
        'ip_address': ip_address,
        'user_agent': user_agent
    }

async def send_twilio_otp_async(phone: str, request_id: str) -> str:
    """Async OTP sending with enhanced error handling"""
    try:
        if not client:
            raise Exception("Twilio client not initialized")
        
        if not settings.TWILIO_VERIFY_SERVICE_SID:
            raise Exception("Twilio Verify Service SID not configured")
        
        # Add request tracking
        logger.info(f"Sending OTP to {phone} (request_id: {request_id})")
        
        verification = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID).verifications.create(
            to=phone, 
            channel="sms"
        )
        
        logger.info(f"OTP sent successfully to {phone}, SID: {verification.sid}")
        return verification.sid
        
    except TwilioRestException as e:
        logger.error(f"Twilio REST error for {phone}: {e.code} - {e.msg}")
        if e.code == 60202:  # Invalid phone number
            raise HTTPException(status_code=400, detail="Invalid phone number")
        elif e.code == 60200:  # Invalid parameter
            raise HTTPException(status_code=400, detail="Invalid request parameters")
        else:
            raise HTTPException(status_code=500, detail="SMS service temporarily unavailable")
            
    except TwilioException as e:
        logger.error(f"Twilio error for {phone}: {e}")
        raise HTTPException(status_code=500, detail="SMS service temporarily unavailable")
        
    except Exception as e:
        logger.error(f"Unexpected error sending OTP to {phone}: {e}")
        raise HTTPException(status_code=500, detail="Failed to send OTP")

async def verify_twilio_otp_async(phone: str, otp: str, request_id: str) -> bool:
    """Async OTP verification with enhanced error handling"""
    try:
        if not client:
            raise Exception("Twilio client not initialized")
        
        if not settings.TWILIO_VERIFY_SERVICE_SID:
            raise Exception("Twilio Verify Service SID not configured")
        
        logger.info(f"Verifying OTP for {phone} (request_id: {request_id})")
        
        verification_check = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID).verification_checks.create(
            to=phone,
            code=otp
        )
        
        is_approved = verification_check.status == "approved"
        logger.info(f"OTP verification for {phone}: {verification_check.status}")
        
        return is_approved
        
    except TwilioRestException as e:
        logger.error(f"Twilio verification error for {phone}: {e.code} - {e.msg}")
        return False
        
    except Exception as e:
        logger.error(f"Unexpected error verifying OTP for {phone}: {e}")
        return False

def cleanup_expired_otps():
    """Clean up expired OTP codes with enhanced logging"""
    try:
        with Session(engine) as session:
            expired_otps = session.exec(
                select(OTPCode).where(OTPCode.expires_at < datetime.utcnow())
            ).all()
            
            count = len(expired_otps)
            for otp in expired_otps:
                session.delete(otp)
            session.commit()
            
            if count > 0:
                logger.info(f"Cleaned up {count} expired OTP codes")
                
    except Exception as e:
        logger.error(f"Error cleaning up expired OTPs: {e}")

def get_client_info(request: Request) -> Dict[str, str]:
    """Extract client information for security"""
    return {
        'ip_address': request.client.host if request.client else None,
        'user_agent': request.headers.get('user-agent'),
        'x_forwarded_for': request.headers.get('x-forwarded-for'),
        'x_real_ip': request.headers.get('x-real-ip'),
        'referer': request.headers.get('referer')
    }

@router.post("/login", response_model=LoginResponse)
async def login_production(
    payload: LoginRequest, 
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Production-ready login API with enhanced security and monitoring
    """
    request_id = str(uuid.uuid4())
    client_info = get_client_info(request)
    
    try:
        # Fraud detection
        fraud_result = detect_fraud(payload.phone, client_info['ip_address'], client_info['user_agent'])
        if fraud_result['risk_level'] == 'high':
            logger.warning(f"High fraud risk detected for {payload.phone}: {fraud_result}")
            audit_log('login_attempt', payload.phone, request_id=request_id, 
                     ip_address=client_info['ip_address'], success=False, 
                     details={'fraud_detected': fraud_result})
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # Rate limiting
        if not check_rate_limit(payload.phone, "login", request_id):
            audit_log('rate_limit_exceeded', payload.phone, request_id=request_id, 
                     ip_address=client_info['ip_address'], success=False)
            raise HTTPException(status_code=429, detail="Too many OTP requests. Please try again later.")
        
        # Check if user exists
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.phone == payload.phone)
            ).first()
            
            if not user:
                audit_log('login_attempt', payload.phone, request_id=request_id, 
                         ip_address=client_info['ip_address'], success=False, 
                         details={'error': 'PHONE_NOT_FOUND'})
                return LoginResponse(
                    success=False,
                    message="Invalid phone number",
                    data={"error": "PHONE_NOT_FOUND"}
                )
        
        # Send OTP via Twilio
        try:
            verification_sid = await send_twilio_otp_async(payload.phone, request_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send OTP: {e}")
            raise HTTPException(status_code=500, detail="Failed to send OTP")
        
        # Store verification attempt in database for tracking
        expires_at = datetime.utcnow() + timedelta(minutes=security_config.otp_expiry_minutes)
        
        with Session(engine) as session:
            otp_code = OTPCode(
                phone=payload.phone,
                otp="",  # We don't store the actual OTP, Twilio handles it
                flow="login",
                expires_at=expires_at
            )
            session.add(otp_code)
            session.commit()
        
        # Audit logging
        audit_log('login_otp_sent', payload.phone, user.id, request_id, 
                 client_info['ip_address'], True, 
                 {'verification_sid': verification_sid, 'fraud_result': fraud_result})
        
        return LoginResponse(
            success=True,
            message="OTP sent successfully",
            data={
                "phone": payload.phone,
                "otp_expires_in": security_config.otp_expiry_minutes * 60,
                "request_id": request_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error for {payload.phone}: {e}")
        audit_log('login_error', payload.phone, request_id=request_id, 
                 ip_address=client_info['ip_address'], success=False, 
                 details={'error': str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/register", response_model=RegisterResponse, status_code=201)
async def register_production(
    payload: RegisterRequest, 
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Production-ready registration API with enhanced security and monitoring
    """
    request_id = str(uuid.uuid4())
    client_info = get_client_info(request)
    
    try:
        # Fraud detection
        fraud_result = detect_fraud(payload.phone, client_info['ip_address'], client_info['user_agent'])
        if fraud_result['risk_level'] == 'high':
            logger.warning(f"High fraud risk detected for registration {payload.phone}: {fraud_result}")
            audit_log('register_attempt', payload.phone, request_id=request_id, 
                     ip_address=client_info['ip_address'], success=False, 
                     details={'fraud_detected': fraud_result})
            raise HTTPException(status_code=429, detail="Too many requests")
        
        # Rate limiting
        if not check_rate_limit(payload.phone, "register", request_id):
            audit_log('rate_limit_exceeded', payload.phone, request_id=request_id, 
                     ip_address=client_info['ip_address'], success=False)
            raise HTTPException(status_code=429, detail="Too many registration requests. Please try again later.")
        
        # Check if user already exists
        with Session(engine) as session:
            existing_user = session.exec(
                select(User).where(User.phone == payload.phone)
            ).first()
            
            if existing_user:
                audit_log('register_attempt', payload.phone, request_id=request_id, 
                         ip_address=client_info['ip_address'], success=False, 
                         details={'error': 'PHONE_ALREADY_EXISTS'})
                return RegisterResponse(
                    success=False,
                    message="Phone number already registered",
                    data={"error": "PHONE_ALREADY_EXISTS"}
                )
        
        # Generate user ID
        user_id = str(uuid.uuid4())
        
        # Save profile image if provided
        profile_image_url = None
        if payload.profile_image:
            try:
                profile_image_url = save_profile_image(payload.profile_image, user_id)
            except Exception as e:
                logger.error(f"Failed to save profile image: {e}")
                # Continue without profile image
        
        # Send OTP via Twilio
        try:
            verification_sid = await send_twilio_otp_async(payload.phone, request_id)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to send OTP: {e}")
            raise HTTPException(status_code=500, detail="Failed to send OTP")
        
        # Save user data to database
        with Session(engine) as session:
            user = User(
                id=user_id,
                name=payload.name,
                phone=payload.phone,
                country_code=extract_country_code(payload.phone),
                age=payload.age,
                date_of_birth=datetime.strptime(payload.date_of_birth, '%Y-%m-%d') if payload.date_of_birth else None,
                profile_image_url=profile_image_url,
                is_verified=False
            )
            session.add(user)
            session.commit()
        
        # Audit logging
        audit_log('register_otp_sent', payload.phone, user_id, request_id, 
                 client_info['ip_address'], True, 
                 {'verification_sid': verification_sid, 'fraud_result': fraud_result})
        
        return RegisterResponse(
            success=True,
            message="Registration successful. OTP sent for verification.",
            data={
                "user_id": user_id,
                "phone": payload.phone,
                "otp_expires_in": security_config.otp_expiry_minutes * 60,
                "request_id": request_id
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Register error for {payload.phone}: {e}")
        audit_log('register_error', payload.phone, request_id=request_id, 
                 ip_address=client_info['ip_address'], success=False, 
                 details={'error': str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/verify-otp", response_model=VerifyOTPResponse)
async def verify_otp_production(
    payload: VerifyOTPRequest, 
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Production-ready OTP verification API with enhanced security and monitoring
    """
    request_id = str(uuid.uuid4())
    client_info = get_client_info(request)
    
    try:
        # Clean up expired OTPs
        background_tasks.add_task(cleanup_expired_otps)
        
        # Verify OTP using Twilio
        is_valid = await verify_twilio_otp_async(payload.phone, payload.otp, request_id)
        
        if not is_valid:
            audit_log('otp_verification_failed', payload.phone, request_id=request_id, 
                     ip_address=client_info['ip_address'], success=False, 
                     details={'flow': payload.flow})
            return VerifyOTPResponse(
                success=False,
                message="Invalid OTP",
                data={"error": "INVALID_OTP"}
            )
        
        # Find user
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.phone == payload.phone)
            ).first()
            
            if not user:
                audit_log('otp_verification_user_not_found', payload.phone, request_id=request_id, 
                         ip_address=client_info['ip_address'], success=False)
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
                expires_at=datetime.utcnow() + timedelta(days=security_config.session_expiry_days)
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
        
        # Audit logging
        audit_log('otp_verification_success', payload.phone, user.id, request_id, 
                 client_info['ip_address'], True, 
                 {'flow': payload.flow})
        
        return VerifyOTPResponse(
            success=True,
            message="OTP verified successfully",
            data={
                "user": user_response.dict(),
                "token": access_token,
                "refresh_token": refresh_token,
                "request_id": request_id
            }
        )
        
    except Exception as e:
        logger.error(f"Verify OTP error for {payload.phone}: {e}")
        audit_log('otp_verification_error', payload.phone, request_id=request_id, 
                 ip_address=client_info['ip_address'], success=False, 
                 details={'error': str(e)})
        raise HTTPException(status_code=500, detail="Internal server error")

# Health check endpoint for production monitoring
@router.get("/health")
async def health_check():
    """Production health check endpoint"""
    try:
        # Check database connection
        with Session(engine) as session:
            session.exec("SELECT 1").first()
        
        # Check Twilio connection
        twilio_status = "healthy" if client else "unhealthy"
        
        return {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "database": "healthy",
                "twilio": twilio_status
            },
            "version": "1.0.0"
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# Metrics endpoint for production monitoring
@router.get("/metrics")
async def get_metrics():
    """Production metrics endpoint"""
    try:
        with Session(engine) as session:
            total_users = session.exec("SELECT COUNT(*) FROM users").first()
            verified_users = session.exec("SELECT COUNT(*) FROM users WHERE is_verified = 1").first()
            total_otps = session.exec("SELECT COUNT(*) FROM otp_codes").first()
            active_sessions = session.exec("SELECT COUNT(*) FROM user_sessions WHERE expires_at > datetime('now')").first()
        
        return {
            "total_users": total_users or 0,
            "verified_users": verified_users or 0,
            "total_otps": total_otps or 0,
            "active_sessions": active_sessions or 0,
            "rate_limit_cache_size": len(_rate_limit_cache),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to collect metrics")
