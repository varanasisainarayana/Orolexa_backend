# app/models.py
from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
import json
import uuid
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(SQLModel, table=True):
    __tablename__ = "users"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(max_length=100)

    phone: str = Field(max_length=20, unique=True, index=True)
    country_code: Optional[str] = Field(max_length=5, default=None)
    age: Optional[int] = Field(default=None)
    date_of_birth: Optional[datetime] = Field(default=None)
    profile_image_url: Optional[str] = Field(max_length=255, default=None)
    email: Optional[str] = Field(max_length=100, default=None)
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    histories: List["AnalysisHistory"] = Relationship(back_populates="user")
    appointments: List["Appointment"] = Relationship(back_populates="user")
    notifications: List["Notification"] = Relationship(back_populates="user")
    device_connections: List["DeviceConnection"] = Relationship(back_populates="user")
    sessions: List["UserSession"] = Relationship(back_populates="user")

class OTPCode(SQLModel, table=True):
    __tablename__ = "otp_codes"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    phone: str = Field(max_length=20, index=True)
    otp: str = Field(max_length=6)
    flow: str = Field(max_length=10)  # 'login' or 'register'
    is_used: bool = Field(default=False)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    token: str = Field(max_length=500, index=True)
    refresh_token: str = Field(max_length=500, index=True)
    device_info: Optional[str] = Field(default=None)  # JSON string
    ip_address: Optional[str] = Field(max_length=45, default=None)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="sessions")

class AnalysisHistory(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    image_url: str
    ai_report: str
    doctor_name: Optional[str] = Field(default="Dr. AI Assistant")
    status: str = Field(default="completed")  # pending, completed, failed
    thumbnail_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="histories")

class Doctor(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str
    specialization: str
    experience: int  # Years of experience
    rating: float = Field(default=0.0)  # Average rating (1-5)
    location: str
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    available_slots: str = Field(default="[]")  # JSON array of available slots
    profile_image: Optional[str] = None
    is_available: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    appointments: List["Appointment"] = Relationship(back_populates="doctor")

class Appointment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    doctor_id: int = Field(foreign_key="doctor.id")
    patient_name: str
    patient_age: int
    issue: str
    appointment_date: datetime
    appointment_time: str  # HH:MM format
    status: str = Field(default="scheduled")  # scheduled, confirmed, cancelled, completed
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="appointments")
    doctor: Optional[Doctor] = Relationship(back_populates="appointments")

class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    type: str  # appointment, analysis, device, health, system
    title: str
    message: str
    read: bool = Field(default=False)
    data: Optional[str] = Field(default=None)  # JSON string for additional data
    created_at: datetime = Field(default_factory=datetime.utcnow)

    user: Optional[User] = Relationship(back_populates="notifications")

class DeviceConnection(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    device_id: str
    device_name: str
    ip_address: Optional[str] = None
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    disconnected_at: Optional[datetime] = None
    is_active: bool = Field(default=True)

    user: Optional[User] = Relationship(back_populates="device_connections")

class UserSettings(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id", unique=True)
    notifications: str = Field(default='{"push_enabled": true, "email_enabled": false, "sms_enabled": true}')
    privacy: str = Field(default='{"data_sharing": true, "analytics": true}')
    preferences: str = Field(default='{"language": "en", "theme": "light", "auto_sync": true}')
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# Legacy OTPRequest model for backward compatibility
class OTPRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mobile_number: str = Field(index=True)
    otp_code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = Field(default=False)

    # Fields for registration flow (stored until verify)
    full_name: Optional[str] = None
    profile_photo_url: Optional[str] = None
