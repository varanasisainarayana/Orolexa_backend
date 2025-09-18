# app/models/appointment.py
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class Appointment(SQLModel, table=True):
    __tablename__ = "appointments"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    doctor_id: int = Field(foreign_key="doctors.id")
    patient_name: str
    patient_age: int
    issue: str
    appointment_date: datetime
    appointment_time: str
    status: str = Field(default="scheduled")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="appointments")
    doctor: Optional["Doctor"] = Relationship(back_populates="appointments")
