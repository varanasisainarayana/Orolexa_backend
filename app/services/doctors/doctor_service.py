# app/services/doctor_service.py
from typing import List, Optional
from sqlmodel import Session, select, and_
from datetime import datetime
import logging

from app.db.models import Doctor
from app.schemas import DoctorCreate, DoctorFilters

logger = logging.getLogger(__name__)

class DoctorService:
    def __init__(self, session: Session):
        self.session = session

    def create_doctor(self, doctor_data: DoctorCreate) -> Optional[Doctor]:
        """Create new doctor"""
        try:
            doctor = Doctor(**doctor_data.dict())
            self.session.add(doctor)
            self.session.commit()
            self.session.refresh(doctor)
            return doctor
        except Exception as e:
            logger.error(f"Error creating doctor: {e}")
            self.session.rollback()
            return None

    def get_doctor_by_id(self, doctor_id: int) -> Optional[Doctor]:
        """Get doctor by ID"""
        try:
            return self.session.exec(select(Doctor).where(Doctor.id == doctor_id)).first()
        except Exception as e:
            logger.error(f"Error getting doctor {doctor_id}: {e}")
            return None

    def get_all_doctors(self, filters: DoctorFilters = None, skip: int = 0, limit: int = 100) -> List[Doctor]:
        """Get all doctors with optional filters"""
        try:
            query = select(Doctor)
            
            if filters:
                if filters.specialization:
                    query = query.where(Doctor.specialization.ilike(f"%{filters.specialization}%"))
                if filters.location:
                    query = query.where(Doctor.location.ilike(f"%{filters.location}%"))
                if filters.rating is not None:
                    query = query.where(Doctor.rating >= filters.rating)
                if filters.available is not None:
                    query = query.where(Doctor.is_available == filters.available)
            
            return self.session.exec(
                query.offset(skip).limit(limit).order_by(Doctor.rating.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting doctors: {e}")
            return []

    def update_doctor(self, doctor_id: int, update_data: dict) -> Optional[Doctor]:
        """Update doctor"""
        try:
            doctor = self.get_doctor_by_id(doctor_id)
            if not doctor:
                return None
            
            for key, value in update_data.items():
                if hasattr(doctor, key) and value is not None:
                    setattr(doctor, key, value)
            
            self.session.add(doctor)
            self.session.commit()
            self.session.refresh(doctor)
            return doctor
        except Exception as e:
            logger.error(f"Error updating doctor {doctor_id}: {e}")
            self.session.rollback()
            return None

    def delete_doctor(self, doctor_id: int) -> bool:
        """Delete doctor"""
        try:
            doctor = self.get_doctor_by_id(doctor_id)
            if not doctor:
                return False
            
            self.session.delete(doctor)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting doctor {doctor_id}: {e}")
            self.session.rollback()
            return False

    def search_doctors(self, query: str, skip: int = 0, limit: int = 100) -> List[Doctor]:
        """Search doctors by name or specialization"""
        try:
            return self.session.exec(
                select(Doctor)
                .where(
                    and_(
                        Doctor.is_available == True,
                        (Doctor.name.ilike(f"%{query}%") | Doctor.specialization.ilike(f"%{query}%"))
                    )
                )
                .offset(skip)
                .limit(limit)
                .order_by(Doctor.rating.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error searching doctors: {e}")
            return []
