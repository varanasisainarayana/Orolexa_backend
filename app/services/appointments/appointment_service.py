# app/services/appointment_service.py
from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime
import logging

from app.db.models import Appointment, Doctor
from app.schemas import AppointmentCreate, AppointmentResponse

logger = logging.getLogger(__name__)

class AppointmentService:
    def __init__(self, session: Session):
        self.session = session

    def create_appointment(self, appointment_data: AppointmentCreate, user_id: str) -> Optional[Appointment]:
        """Create new appointment"""
        try:
            appointment = Appointment(
                user_id=user_id,
                **appointment_data.dict()
            )
            self.session.add(appointment)
            self.session.commit()
            self.session.refresh(appointment)
            return appointment
        except Exception as e:
            logger.error(f"Error creating appointment: {e}")
            self.session.rollback()
            return None

    def get_appointment_by_id(self, appointment_id: int) -> Optional[Appointment]:
        """Get appointment by ID"""
        try:
            return self.session.exec(select(Appointment).where(Appointment.id == appointment_id)).first()
        except Exception as e:
            logger.error(f"Error getting appointment {appointment_id}: {e}")
            return None

    def get_user_appointments(self, user_id: str, skip: int = 0, limit: int = 100) -> List[Appointment]:
        """Get user's appointments"""
        try:
            return self.session.exec(
                select(Appointment)
                .where(Appointment.user_id == user_id)
                .offset(skip)
                .limit(limit)
                .order_by(Appointment.appointment_date.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting user appointments: {e}")
            return []

    def update_appointment_status(self, appointment_id: int, status: str) -> bool:
        """Update appointment status"""
        try:
            appointment = self.get_appointment_by_id(appointment_id)
            if not appointment:
                return False
            
            appointment.status = status
            self.session.add(appointment)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating appointment status: {e}")
            self.session.rollback()
            return False

    def delete_appointment(self, appointment_id: int) -> bool:
        """Delete appointment"""
        try:
            appointment = self.get_appointment_by_id(appointment_id)
            if not appointment:
                return False
            
            self.session.delete(appointment)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting appointment: {e}")
            self.session.rollback()
            return False

    def get_doctor_appointments(self, doctor_id: int, skip: int = 0, limit: int = 100) -> List[Appointment]:
        """Get doctor's appointments"""
        try:
            return self.session.exec(
                select(Appointment)
                .where(Appointment.doctor_id == doctor_id)
                .offset(skip)
                .limit(limit)
                .order_by(Appointment.appointment_date.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting doctor appointments: {e}")
            return []
