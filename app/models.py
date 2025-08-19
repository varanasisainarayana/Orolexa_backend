# app/models.py (snippet)
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    full_name: Optional[str] = None
    mobile_number: str = Field(index=True, unique=True, nullable=False)
    profile_photo_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    histories: List["AnalysisHistory"] = Relationship(back_populates="user")

class OTPRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mobile_number: str = Field(index=True)
    otp_code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = Field(default=False)

    # NEW fields for registration flow (stored until verify)
    full_name: Optional[str] = None
    profile_photo_url: Optional[str] = None

class AnalysisHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    image_url: str
    ai_report: str
    doctor_name: Optional[str] = Field(default="Dr. AI Assistant")
    status: str = Field(default="completed")  # pending, completed, failed
    thumbnail_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="histories")
