# app/schemas/analysis.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class AnalysisResponse(BaseModel):
    id: int
    analysis: str
    image_url: str
    thumbnail_url: Optional[str] = None
    doctor_name: str
    status: str
    timestamp: str

class AnalysisHistoryResponse(BaseModel):
    success: bool
    data: List[AnalysisResponse]
