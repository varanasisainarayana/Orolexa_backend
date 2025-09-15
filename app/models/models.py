from typing import Optional, List
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
import uuid
from sqlalchemy import Column, LargeBinary


class User(SQLModel, table=True):
    __tablename__ = "users"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    name: str = Field(max_length=100)
    phone: str = Field(max_length=20, unique=True, index=True)
    country_code: Optional[str] = Field(max_length=5, default=None)
    age: Optional[int] = Field(default=None)
    date_of_birth: Optional[datetime] = Field(default=None)
    profile_image_url: Optional[str] = Field(max_length=255, default=None)
    profile_image_id: Optional[str] = Field(default=None)
    email: Optional[str] = Field(max_length=100, default=None)
    is_verified: bool = Field(default=False)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

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
    flow: str = Field(max_length=10)
    is_used: bool = Field(default=False)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)


class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    token: str = Field(max_length=500, index=True)
    refresh_token: str = Field(max_length=500, index=True)
    device_info: Optional[str] = Field(default=None)
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
    status: str = Field(default="completed")
    thumbnail_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user: Optional[User] = Relationship(back_populates="histories")


class Doctor(SQLModel, table=True):
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
    appointments: List["Appointment"] = Relationship(back_populates="doctor")


class Appointment(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    doctor_id: int = Field(foreign_key="doctor.id")
    patient_name: str
    patient_age: int
    issue: str
    appointment_date: datetime
    appointment_time: str
    status: str = Field(default="scheduled")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    user: Optional[User] = Relationship(back_populates="appointments")
    doctor: Optional[Doctor] = Relationship(back_populates="appointments")


class Notification(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    type: str
    title: str
    message: str
    read: bool = Field(default=False)
    data: Optional[str] = Field(default=None)
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


class OTPRequest(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    mobile_number: str = Field(index=True)
    otp_code: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    is_verified: bool = Field(default=False)
    full_name: Optional[str] = None
    profile_photo_url: Optional[str] = None


class ImageStorage(SQLModel, table=True):
    __tablename__ = "image_storage"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    filename: str = Field(max_length=255)
    content_type: str = Field(max_length=100)
    file_size: int
    image_data: bytes = Field(sa_column=Column(LargeBinary))
    image_type: str = Field(max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_id: Optional[str] = Field(foreign_key="image_storage.id", default=None)


