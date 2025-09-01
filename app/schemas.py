from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from enum import Enum


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
# IP Address Streaming Schemas
# =========================
class IPAddressRequest(BaseModel):
    ip_address: str


class StreamDataResponse(BaseModel):
    ip_address: str
    timestamp: str
    data: str
    status: str


# =========================
# ESP32-CAM Specific Schemas
# =========================
class ESP32DataRequest(BaseModel):
    ip_address: str
    timestamp: str
    data: str
    status: str
    device_type: str = "esp32_cam"
    rssi: Optional[int] = None
    free_heap: Optional[int] = None
    temperature: Optional[float] = None
    humidity: Optional[float] = None
    motion_detected: Optional[bool] = None
    image_captured: Optional[bool] = None


class ESP32DeviceInfo(BaseModel):
    ip_address: str
    device_type: str
    mac_address: Optional[str] = None
    firmware_version: Optional[str] = None
    uptime: Optional[int] = None
    last_seen: Optional[str] = None
    status: str = "online"


class ESP32ImageUpload(BaseModel):
    ip_address: str
    image_data: str  # Base64 encoded image
    timestamp: str
    image_type: str = "jpeg"
    resolution: Optional[str] = None


# =========================
# ESP32-CAM API Schemas (Based on your requirements)
# =========================

class ESP32ConnectionTestRequest(BaseModel):
    ipAddress: str
    port: int = 81
    streamPath: str = "/stream"


class ESP32ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    connectionDetails: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class AnalysisType(str, Enum):
    dental = "dental"
    general = "general"
    custom = "custom"


class Priority(str, Enum):
    low = "low"
    normal = "normal"
    high = "high"


class ESP32ImageAnalysisRequest(BaseModel):
    images: List[str]  # Base64 encoded images
    metadata: Dict[str, Any]
    analysisPreferences: Optional[Dict[str, Any]] = None


class ESP32ImageAnalysisResponse(BaseModel):
    status: str  # 'completed' | 'processing' | 'failed'
    analysisId: str
    results: Optional[Dict[str, Any]] = None
    processingTime: int
    timestamp: str
    error: Optional[str] = None
    nextSteps: Optional[List[str]] = None


class ESP32StreamStatusResponse(BaseModel):
    deviceId: str
    isActive: bool
    lastSeen: str
    streamQuality: str  # 'excellent' | 'good' | 'fair' | 'poor'
    connectionStats: Dict[str, Any]
    deviceInfo: Optional[Dict[str, Any]] = None


class SessionType(str, Enum):
    analysis = "analysis"
    monitoring = "monitoring"
    diagnostic = "diagnostic"


class ESP32SessionRequest(BaseModel):
    deviceId: str
    ipAddress: str
    port: int = 81
    streamPath: str = "/stream"
    userId: Optional[str] = None
    sessionType: SessionType = SessionType.analysis


class ESP32SessionResponse(BaseModel):
    sessionId: str
    deviceId: str
    status: str  # 'active' | 'paused' | 'ended'
    startTime: str
    endTime: Optional[str] = None
    totalImages: int
    analysisCount: int
    sessionUrl: str


class ESP32ImageUploadRequest(BaseModel):
    sessionId: str
    deviceId: str
    image: str  # Base64 encoded
    imageType: str = "jpeg"
    timestamp: str
    metadata: Optional[Dict[str, Any]] = None


class ESP32ImageUploadResponse(BaseModel):
    success: bool
    imageId: str
    url: str
    thumbnailUrl: Optional[str] = None
    message: str


# =========================
# Common Response Schemas
# =========================
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
