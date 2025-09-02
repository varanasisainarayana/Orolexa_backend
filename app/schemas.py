from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
import re
import base64
from PIL import Image
import io

# =========================
# Authentication Schemas
# =========================

class LoginRequest(BaseModel):
    phone: str = Field(..., description="Phone number with country code (e.g., +1234567890)")

    @validator('phone')
    def validate_phone(cls, v):
        # Remove any non-digit characters except +
        phone_clean = re.sub(r'[^\d+]', '', v)
        if not re.match(r'^\+\d{1,4}\d{6,14}$', phone_clean):
            raise ValueError('Invalid phone number format. Must include country code (e.g., +1234567890)')
        return phone_clean

class LoginResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class RegisterRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="User's full name")
    phone: str = Field(..., description="Phone number with country code (e.g., +1234567890)")
    age: Optional[int] = Field(None, ge=1, le=120, description="User's age")
    profile_image: Optional[str] = Field(None, description="Profile image (base64 encoded, file path, or data URL)")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format")

    @validator('name')
    def validate_name(cls, v):
        if not re.match(r'^[a-zA-Z\s\-]+$', v):
            raise ValueError('Name can only contain letters, spaces, and hyphens')
        return v.strip()

    @validator('phone')
    def validate_phone(cls, v):
        phone_clean = re.sub(r'[^\d+]', '', v)
        if not re.match(r'^\+\d{1,4}\d{6,14}$', phone_clean):
            raise ValueError('Invalid phone number format. Must include country code (e.g., +1234567890)')
        return phone_clean

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 1 or v > 120):
            raise ValueError('Age must be between 1 and 120')
        return v

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        if v is not None:
            try:
                dob = datetime.strptime(v, '%Y-%m-%d')
                if dob > datetime.now():
                    raise ValueError('Date of birth cannot be in the future')
                if (datetime.now() - dob).days > 43800:  # 120 years
                    raise ValueError('Date of birth is too far in the past')
            except ValueError as e:
                if 'Date of birth' in str(e):
                    raise e
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v

    @validator('profile_image')
    def validate_profile_image(cls, v):
        if v is not None:
            try:
                # Handle different profile image formats
                if v.startswith('data:image/'):
                    # Base64 encoded image with data URL
                    header, data = v.split(',', 1)
                    image_data = base64.b64decode(data)
                elif v.startswith('file://'):
                    # File path from mobile app - we'll handle this in the backend
                    # For now, just validate it's a valid file path
                    if not v.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        raise ValueError('Profile image must be a valid image file (JPG, PNG, WebP)')
                    return v  # Return as-is for backend processing
                elif v.startswith('/'):
                    # Absolute file path
                    if not v.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        raise ValueError('Profile image must be a valid image file (JPG, PNG, WebP)')
                    return v  # Return as-is for backend processing
                else:
                    # Try to decode as base64 without data URL prefix
                    try:
                        image_data = base64.b64decode(v)
                    except:
                        raise ValueError('Profile image must be a valid base64 encoded image or file path')
                
                # Check file size (5MB limit) for base64 images
                if len(image_data) > 5 * 1024 * 1024:
                    raise ValueError('Profile image size must be less than 5MB')
                
                # Validate image format for base64 images
                image = Image.open(io.BytesIO(image_data))
                if image.format not in ['JPEG', 'PNG', 'WEBP']:
                    raise ValueError('Profile image must be JPEG, PNG, or WebP format')
                
            except Exception as e:
                if 'Profile image' in str(e):
                    raise e
                raise ValueError('Invalid profile image format')
        return v

class RegisterResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class VerifyOTPRequest(BaseModel):
    # Support both old production format and new format
    phone: Optional[str] = Field(None, description="Phone number with country code (new format)")
    mobile_number: Optional[str] = Field(None, description="Phone number with country code (old format)")
    otp: Optional[str] = Field(None, description="6-digit OTP (new format)")
    otp_code: Optional[str] = Field(None, description="6-digit OTP (old format)")
    flow: Optional[str] = Field(None, description="Flow type: 'login' or 'register'")

    class Config:
        # Allow extra fields for backward compatibility
        extra = "allow"

    @validator('phone', 'mobile_number')
    def validate_phone(cls, v):
        if v is not None:
            phone_clean = re.sub(r'[^\d+]', '', v)
            if not re.match(r'^\+\d{1,4}\d{6,14}$', phone_clean):
                raise ValueError('Invalid phone number format')
            return phone_clean
        return v

    @validator('otp', 'otp_code')
    def validate_otp(cls, v):
        if v is not None:
            if not v.isdigit() or len(v) != 6:
                raise ValueError('OTP must be 6 digits')
        return v

    @validator('flow')
    def validate_flow(cls, v):
        if v is not None and v not in ['login', 'register']:
            raise ValueError('Flow must be either "login" or "register"')
        return v

    def get_phone(self) -> str:
        """Get phone number from either field"""
        return self.phone or self.mobile_number

    def get_otp(self) -> str:
        """Get OTP from either field"""
        return self.otp or self.otp_code

    def get_flow(self) -> str:
        """Get flow, default to 'login' if not provided"""
        return self.flow or 'login'

class VerifyOTPResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class ResendOTPRequest(BaseModel):
    phone: str = Field(..., description="Phone number with country code")

    @validator('phone')
    def validate_phone(cls, v):
        phone_clean = re.sub(r'[^\d+]', '', v)
        if not re.match(r'^\+\d{1,4}\d{6,14}$', phone_clean):
            raise ValueError('Invalid phone number format')
        return phone_clean

class ResendOTPResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class UserResponse(BaseModel):
    id: str
    name: str
    phone: str
    age: Optional[int] = None
    profile_image_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    refresh_token: str

# =========================
# Doctor Schemas
# =========================
class DoctorBase(BaseModel):
    name: str
    specialization: str
    experience: int
    rating: float = Field(ge=0, le=5)
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    available_slots: List[str] = []
    profile_image: Optional[str] = None
    is_available: bool = True

class DoctorCreate(DoctorBase):
    pass

class DoctorResponse(DoctorBase):
    id: int
    created_at: datetime

class DoctorFilters(BaseModel):
    specialization: Optional[str] = None
    location: Optional[str] = None
    rating: Optional[float] = None
    available: Optional[bool] = None


# =========================
# Appointment Schemas
# =========================
class AppointmentBase(BaseModel):
    doctor_id: int
    patient_name: str
    patient_age: int = Field(ge=0, le=120)
    issue: str
    appointment_date: str  # YYYY-MM-DD
    appointment_time: str  # HH:MM

class AppointmentCreate(AppointmentBase):
    pass

class AppointmentResponse(AppointmentBase):
    id: int
    doctor_name: str
    status: str
    created_at: datetime


# =========================
# Notification Schemas
# =========================
class NotificationBase(BaseModel):
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    read: bool
    created_at: datetime

class NotificationFilters(BaseModel):
    type: Optional[str] = None
    read: Optional[bool] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0


# =========================
# Device Schemas
# =========================
class DeviceConnectionBase(BaseModel):
    device_id: str
    device_name: str
    ip_address: Optional[str] = None

class DeviceConnectionCreate(DeviceConnectionBase):
    pass

class DeviceConnectionResponse(DeviceConnectionBase):
    id: int
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    is_active: bool

class DeviceStatus(BaseModel):
    connected: bool
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    last_seen: Optional[datetime] = None
    battery_level: Optional[int] = None
    firmware_version: Optional[str] = None


# =========================
# Health & Analytics Schemas
# =========================
class HealthSummary(BaseModel):
    total_analyses: int
    last_analysis_date: Optional[str] = None
    health_score: int = Field(ge=0, le=100)
    recommendations: List[str] = []
    next_checkup_date: Optional[str] = None

class AnalyticsData(BaseModel):
    period: str
    data: List[Dict[str, Any]]
    summary: Dict[str, Any]


# =========================
# Settings Schemas
# =========================
class NotificationSettings(BaseModel):
    push_enabled: bool = True
    email_enabled: bool = False
    sms_enabled: bool = True

class PrivacySettings(BaseModel):
    data_sharing: bool = True
    analytics: bool = True

class PreferenceSettings(BaseModel):
    language: str = "en"
    theme: str = "light"
    auto_sync: bool = True

class AppSettings(BaseModel):
    notifications: NotificationSettings
    privacy: PrivacySettings
    preferences: PreferenceSettings

class UpdateSettingsRequest(BaseModel):
    notifications: Optional[NotificationSettings] = None
    privacy: Optional[PrivacySettings] = None
    preferences: Optional[PreferenceSettings] = None


# =========================
# Common Response Schemas
# =========================
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    items: List[Any]
    pagination: Dict[str, Any]

# =========================
# Error Response Schemas
# =========================
class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error: str
    status_code: Optional[int] = None

# =========================
# Profile Management Schemas
# =========================
class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="User's full name")
    age: Optional[int] = Field(None, ge=1, le=120, description="User's age")
    profile_image: Optional[str] = Field(None, description="Profile image (base64 encoded, file path, or data URL)")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z\s\-]+$', v):
                raise ValueError('Name can only contain letters, spaces, and hyphens')
            return v.strip()
        return v

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 1 or v > 120):
            raise ValueError('Age must be between 1 and 120')
        return v

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        if v is not None:
            try:
                dob = datetime.strptime(v, '%Y-%m-%d')
                if dob > datetime.now():
                    raise ValueError('Date of birth cannot be in the future')
                if (datetime.now() - dob).days > 43800:  # 120 years
                    raise ValueError('Date of birth is too far in the past')
            except ValueError as e:
                if 'Date of birth' in str(e):
                    raise e
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v

    @validator('profile_image')
    def validate_profile_image(cls, v):
        if v is not None:
            try:
                # Handle different profile image formats
                if v.startswith('data:image/'):
                    # Base64 encoded image with data URL
                    header, data = v.split(',', 1)
                    image_data = base64.b64decode(data)
                elif v.startswith('file://'):
                    # File path from mobile app - we'll handle this in the backend
                    # For now, just validate it's a valid file path
                    if not v.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        raise ValueError('Profile image must be a valid image file (JPG, PNG, WebP)')
                    return v  # Return as-is for backend processing
                elif v.startswith('/'):
                    # Absolute file path
                    if not v.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                        raise ValueError('Profile image must be a valid image file (JPG, PNG, WebP)')
                    return v  # Return as-is for backend processing
                else:
                    # Try to decode as base64 without data URL prefix
                    try:
                        image_data = base64.b64decode(v)
                    except:
                        raise ValueError('Profile image must be a valid base64 encoded image or file path')
                
                # Check file size (5MB limit) for base64 images
                if len(image_data) > 5 * 1024 * 1024:
                    raise ValueError('Profile image size must be less than 5MB')
                
                # Validate image format for base64 images
                image = Image.open(io.BytesIO(image_data))
                if image.format not in ['JPEG', 'PNG', 'WEBP']:
                    raise ValueError('Profile image must be JPEG, PNG, or WebP format')
                
            except Exception as e:
                if 'Profile image' in str(e):
                    raise e
                raise ValueError('Invalid profile image format')
        return v

class UpdateProfileResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class UploadImageRequest(BaseModel):
    """Legacy base64 upload request - kept for backward compatibility"""
    image: str = Field(..., description="Base64 encoded image")

    @validator('image')
    def validate_image(cls, v):
        try:
            if v.startswith('data:image/'):
                # Base64 encoded image with data URL
                header, data = v.split(',', 1)
                image_data = base64.b64decode(data)
            else:
                # Try to decode as base64 without data URL prefix
                image_data = base64.b64decode(v)
            
            # Check file size (5MB limit)
            if len(image_data) > 5 * 1024 * 1024:
                raise ValueError('Image size must be less than 5MB')
            
            # Validate image format
            image = Image.open(io.BytesIO(image_data))
            if image.format not in ['JPEG', 'PNG', 'WEBP']:
                raise ValueError('Image must be JPEG, PNG, or WebP format')
            
        except Exception as e:
            if 'Image' in str(e):
                raise e
            raise ValueError('Invalid image format')
        return v

class UploadImageResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class DeleteImageResponse(BaseModel):
    success: bool
    message: str

class DeleteAccountRequest(BaseModel):
    password_confirmation: str = Field(..., description="Type 'DELETE' to confirm account deletion")
    
    @validator('password_confirmation')
    def validate_confirmation(cls, v):
        if v != 'DELETE':
            raise ValueError('Please type DELETE to confirm account deletion')
        return v

class DeleteAccountResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None

# =========================
# Legacy Schemas (for backward compatibility)
# =========================
class SendOTPRequest(BaseModel):
    mobile_number: str

class RegisterVerifyRequest(BaseModel):
    mobile_number: str
    otp_code: str
    full_name: str
    profile_photo_url: str
