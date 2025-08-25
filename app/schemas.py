from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


# =========================
# OTP Send Requests
# =========================
class SendOTPRequest(BaseModel):
    mobile_number: str


# =========================
# OTP Verify Requests (Login)
# =========================
class VerifyOTPRequest(BaseModel):
    mobile_number: str
    otp_code: str


# =========================
# OTP Verify Requests (Registration)
# =========================
class RegisterVerifyRequest(BaseModel):
    mobile_number: str
    otp_code: str
    full_name: str  # REQUIRED for registration
    profile_photo_url: str  # REQUIRED for registration


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
