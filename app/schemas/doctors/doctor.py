# app/schemas/doctor.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

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
