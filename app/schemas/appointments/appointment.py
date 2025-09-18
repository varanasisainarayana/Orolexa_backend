# app/schemas/appointment.py
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime

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
