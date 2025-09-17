# app/schemas/common.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class ErrorResponse(BaseModel):
    success: bool = False
    message: str
    error: str
    status_code: Optional[int] = None

class MessageResponse(BaseModel):
    message: str

class PaginatedResponse(BaseModel):
    items: List[Any]
    pagination: Dict[str, Any]

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

# Health & Analytics Schemas
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

# ESP32-CAM Schemas
class ESP32ConnectionTestRequest(BaseModel):
    ipAddress: str
    port: int = 81

class ESP32ConnectionTestResponse(BaseModel):
    success: bool
    message: str
    connectionDetails: Optional[Dict[str, Any]] = None
    error: Optional[str] = None

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
