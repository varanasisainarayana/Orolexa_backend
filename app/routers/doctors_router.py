from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select
import logging

from ..db.session import get_session
from ..db.models.health.doctor import Doctor
from ..db.models.users.user import User
from ..schemas.doctors.doctor import DoctorCreate, DoctorResponse, DoctorFilters
from ..services.auth import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/doctors", tags=["Doctors"])

oauth2_scheme = HTTPBearer()

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
    specialization: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    rating: Optional[float] = Query(None, ge=0, le=5),
    available: Optional[bool] = Query(None),
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        query = select(Doctor)
        if specialization:
            query = query.where(Doctor.specialization.ilike(f"%{specialization}%"))
        if location:
            query = query.where(Doctor.location.ilike(f"%{location}%"))
        if rating is not None:
            query = query.where(Doctor.rating >= rating)
        if available is not None:
            query = query.where(Doctor.is_available == available)
        doctors = session.exec(query).all()
        return [
            DoctorResponse(
                id=d.id,
                name=d.name,
                specialization=d.specialization,
                experience=d.experience,
                rating=d.rating,
                location=d.location,
                latitude=d.latitude,
                longitude=d.longitude,
                available_slots=d.available_slots.split(',') if d.available_slots else [],
                profile_image=d.profile_image,
                is_available=d.is_available,
                created_at=d.created_at,
            )
            for d in doctors
        ]
    except Exception as e:
        logger.error(f"Error retrieving doctors: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve doctors")


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        d = session.exec(select(Doctor).where(Doctor.id == doctor_id)).first()
        if not d:
            raise HTTPException(status_code=404, detail="Doctor not found")
        return DoctorResponse(
            id=d.id,
            name=d.name,
            specialization=d.specialization,
            experience=d.experience,
            rating=d.rating,
            location=d.location,
            latitude=d.latitude,
            longitude=d.longitude,
            available_slots=d.available_slots.split(',') if d.available_slots else [],
            profile_image=d.profile_image,
            is_available=d.is_available,
            created_at=d.created_at,
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
    session: Session = Depends(get_session),
):
    try:
        d = Doctor(
            name=doctor_data.name,
            specialization=doctor_data.specialization,
            experience=doctor_data.experience,
            rating=doctor_data.rating,
            location=doctor_data.location,
            latitude=doctor_data.latitude,
            longitude=doctor_data.longitude,
            available_slots=','.join(doctor_data.available_slots) if doctor_data.available_slots else "",
            profile_image=doctor_data.profile_image,
            is_available=doctor_data.is_available,
        )
        session.add(d)
        session.commit()
        session.refresh(d)
        return DoctorResponse(
            id=d.id,
            name=d.name,
            specialization=d.specialization,
            experience=d.experience,
            rating=d.rating,
            location=d.location,
            latitude=d.latitude,
            longitude=d.longitude,
            available_slots=d.available_slots.split(',') if d.available_slots else [],
            profile_image=d.profile_image,
            is_available=d.is_available,
            created_at=d.created_at,
        )
    except Exception as e:
        logger.error(f"Error creating doctor: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create doctor")


@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id: int,
    doctor_data: DoctorCreate,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    try:
        d = session.exec(select(Doctor).where(Doctor.id == doctor_id)).first()
        if not d:
            raise HTTPException(status_code=404, detail="Doctor not found")
        d.name = doctor_data.name
        d.specialization = doctor_data.specialization
        d.experience = doctor_data.experience
        d.rating = doctor_data.rating
        d.location = doctor_data.location
        d.latitude = doctor_data.latitude
        d.longitude = doctor_data.longitude
        d.available_slots = ','.join(doctor_data.available_slots) if doctor_data.available_slots else ""
        d.profile_image = doctor_data.profile_image
        d.is_available = doctor_data.is_available
        session.add(d)
        session.commit()
        session.refresh(d)
        return DoctorResponse(
            id=d.id,
            name=d.name,
            specialization=d.specialization,
            experience=d.experience,
            rating=d.rating,
            location=d.location,
            latitude=d.latitude,
            longitude=d.longitude,
            available_slots=d.available_slots.split(',') if d.available_slots else [],
            profile_image=d.profile_image,
            is_available=d.is_available,
            created_at=d.created_at,
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
    session: Session = Depends(get_session),
):
    try:
        d = session.exec(select(Doctor).where(Doctor.id == doctor_id)).first()
        if not d:
            raise HTTPException(status_code=404, detail="Doctor not found")
        session.delete(d)
        session.commit()
        return {"success": True, "message": "Doctor deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting doctor {doctor_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete doctor")


