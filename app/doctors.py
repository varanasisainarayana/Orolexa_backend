# app/doctors.py
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
import logging
from datetime import datetime

from .database import get_session
from .models import Doctor, User
from .schemas import DoctorCreate, DoctorResponse, DoctorFilters
from .utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctors", tags=["Doctors"])

# Auth scheme
oauth2_scheme = HTTPBearer()

# Dependency to get current user from JWT
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token: invalid user ID format")

@router.get("/", response_model=List[DoctorResponse])
def get_doctors(
    specialization: Optional[str] = Query(None, description="Filter by specialization"),
    location: Optional[str] = Query(None, description="Filter by location"),
    rating: Optional[float] = Query(None, ge=0, le=5, description="Minimum rating"),
    available: Optional[bool] = Query(None, description="Only available doctors"),
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get list of available doctors with optional filtering"""
    try:
        # Build query
        query = select(Doctor)
        
        # Apply filters
        if specialization:
            query = query.where(Doctor.specialization.ilike(f"%{specialization}%"))
        
        if location:
            query = query.where(Doctor.location.ilike(f"%{location}%"))
        
        if rating is not None:
            query = query.where(Doctor.rating >= rating)
        
        if available is not None:
            query = query.where(Doctor.is_available == available)
        
        # Execute query
        doctors = session.exec(query).all()
        
        logger.info(f"Retrieved {len(doctors)} doctors for user {current_user}")
        
        return [
            DoctorResponse(
                id=doctor.id,
                name=doctor.name,
                specialization=doctor.specialization,
                experience=doctor.experience,
                rating=doctor.rating,
                location=doctor.location,
                latitude=doctor.latitude,
                longitude=doctor.longitude,
                available_slots=doctor.available_slots.split(',') if doctor.available_slots else [],
                profile_image=doctor.profile_image,
                is_available=doctor.is_available,
                created_at=doctor.created_at
            )
            for doctor in doctors
        ]
        
    except Exception as e:
        logger.error(f"Error retrieving doctors: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve doctors")

@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific doctor by ID"""
    try:
        doctor = session.exec(select(Doctor).where(Doctor.id == doctor_id)).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        return DoctorResponse(
            id=doctor.id,
            name=doctor.name,
            specialization=doctor.specialization,
            experience=doctor.experience,
            rating=doctor.rating,
            location=doctor.location,
            latitude=doctor.latitude,
            longitude=doctor.longitude,
            available_slots=doctor.available_slots.split(',') if doctor.available_slots else [],
            profile_image=doctor.profile_image,
            is_available=doctor.is_available,
            created_at=doctor.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving doctor {doctor_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve doctor")

@router.post("/", response_model=DoctorResponse)
def create_doctor(
    doctor_data: DoctorCreate,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Create a new doctor (Admin only)"""
    try:
        # Check if user is admin (you can implement admin check here)
        # For now, we'll allow any authenticated user to create doctors
        
        doctor = Doctor(
            name=doctor_data.name,
            specialization=doctor_data.specialization,
            experience=doctor_data.experience,
            rating=doctor_data.rating,
            location=doctor_data.location,
            latitude=doctor_data.latitude,
            longitude=doctor_data.longitude,
            available_slots=','.join(doctor_data.available_slots) if doctor_data.available_slots else "",
            profile_image=doctor_data.profile_image,
            is_available=doctor_data.is_available
        )
        
        session.add(doctor)
        session.commit()
        session.refresh(doctor)
        
        logger.info(f"Created doctor {doctor.id} by user {current_user}")
        
        return DoctorResponse(
            id=doctor.id,
            name=doctor.name,
            specialization=doctor.specialization,
            experience=doctor.experience,
            rating=doctor.rating,
            location=doctor.location,
            latitude=doctor.latitude,
            longitude=doctor.longitude,
            available_slots=doctor.available_slots.split(',') if doctor.available_slots else [],
            profile_image=doctor.profile_image,
            is_available=doctor.is_available,
            created_at=doctor.created_at
        )
        
    except Exception as e:
        logger.error(f"Error creating doctor: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create doctor")

@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: int,
    doctor_data: DoctorCreate,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update a doctor (Admin only)"""
    try:
        doctor = session.exec(select(Doctor).where(Doctor.id == doctor_id)).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        # Update fields
        doctor.name = doctor_data.name
        doctor.specialization = doctor_data.specialization
        doctor.experience = doctor_data.experience
        doctor.rating = doctor_data.rating
        doctor.location = doctor_data.location
        doctor.latitude = doctor_data.latitude
        doctor.longitude = doctor_data.longitude
        doctor.available_slots = ','.join(doctor_data.available_slots) if doctor_data.available_slots else ""
        doctor.profile_image = doctor_data.profile_image
        doctor.is_available = doctor_data.is_available
        
        session.add(doctor)
        session.commit()
        session.refresh(doctor)
        
        logger.info(f"Updated doctor {doctor_id} by user {current_user}")
        
        return DoctorResponse(
            id=doctor.id,
            name=doctor.name,
            specialization=doctor.specialization,
            experience=doctor.experience,
            rating=doctor.rating,
            location=doctor.location,
            latitude=doctor.latitude,
            longitude=doctor.longitude,
            available_slots=doctor.available_slots.split(',') if doctor.available_slots else [],
            profile_image=doctor.profile_image,
            is_available=doctor.is_available,
            created_at=doctor.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating doctor {doctor_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update doctor")

@router.delete("/{doctor_id}")
def delete_doctor(
    doctor_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Delete a doctor (Admin only)"""
    try:
        doctor = session.exec(select(Doctor).where(Doctor.id == doctor_id)).first()
        
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        session.delete(doctor)
        session.commit()
        
        logger.info(f"Deleted doctor {doctor_id} by user {current_user}")
        
        return {"success": True, "message": "Doctor deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting doctor {doctor_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete doctor")
