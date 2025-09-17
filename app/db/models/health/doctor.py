# app/models/doctor.py
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class Doctor(SQLModel, table=True):
    __tablename__ = "doctors"
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    specialization: str
    experience: int
    rating: float = Field(default=0.0)
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    available_slots: str = Field(default="[]")
    profile_image: Optional[str] = None
    is_available: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    appointments: List["Appointment"] = Relationship(back_populates="doctor")
