# app/appointments.py
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import logging
from datetime import datetime, date

from .database import get_session
from .models import Appointment, Doctor, User
from .schemas import AppointmentCreate, AppointmentResponse
from .utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["Appointments"])

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

@router.post("/", response_model=AppointmentResponse)
def book_appointment(
    appointment_data: AppointmentCreate,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Book a new appointment"""
    try:
        # Verify doctor exists
        doctor = session.exec(select(Doctor).where(Doctor.id == appointment_data.doctor_id)).first()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        
        if not doctor.is_available:
            raise HTTPException(status_code=400, detail="Doctor is not available")
        
        # Parse appointment date
        try:
            appointment_date = datetime.strptime(appointment_data.appointment_date, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid appointment date format. Use YYYY-MM-DD")
        
        # Check if appointment date is in the future
        if appointment_date < date.today():
            raise HTTPException(status_code=400, detail="Appointment date cannot be in the past")
        
        # Validate appointment time format
        try:
            datetime.strptime(appointment_data.appointment_time, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid appointment time format. Use HH:MM")
        
        # Check if slot is available (you can implement more sophisticated slot checking here)
        existing_appointment = session.exec(
            select(Appointment)
            .where(Appointment.doctor_id == appointment_data.doctor_id)
            .where(Appointment.appointment_date == appointment_date)
            .where(Appointment.appointment_time == appointment_data.appointment_time)
            .where(Appointment.status.in_(["scheduled", "confirmed"]))
        ).first()
        
        if existing_appointment:
            raise HTTPException(status_code=400, detail="This time slot is already booked")
        
        # Create appointment
        appointment = Appointment(
            user_id=current_user,
            doctor_id=appointment_data.doctor_id,
            patient_name=appointment_data.patient_name,
            patient_age=appointment_data.patient_age,
            issue=appointment_data.issue,
            appointment_date=appointment_date,
            appointment_time=appointment_data.appointment_time,
            status="scheduled"
        )
        
        session.add(appointment)
        session.commit()
        session.refresh(appointment)
        
        logger.info(f"Booked appointment {appointment.id} for user {current_user}")
        
        return AppointmentResponse(
            id=appointment.id,
            doctor_id=appointment.doctor_id,
            doctor_name=doctor.name,
            patient_name=appointment.patient_name,
            patient_age=appointment.patient_age,
            issue=appointment.issue,
            appointment_date=appointment.appointment_date.strftime("%Y-%m-%d"),
            appointment_time=appointment.appointment_time,
            status=appointment.status,
            created_at=appointment.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to book appointment")

@router.get("/", response_model=List[AppointmentResponse])
def get_user_appointments(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get all appointments for the current user"""
    try:
        appointments = session.exec(
            select(Appointment)
            .where(Appointment.user_id == current_user)
            .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        ).all()
        
        logger.info(f"Retrieved {len(appointments)} appointments for user {current_user}")
        
        result = []
        for appointment in appointments:
            doctor = session.exec(select(Doctor).where(Doctor.id == appointment.doctor_id)).first()
            doctor_name = doctor.name if doctor else "Unknown Doctor"
            
            result.append(AppointmentResponse(
                id=appointment.id,
                doctor_id=appointment.doctor_id,
                doctor_name=doctor_name,
                patient_name=appointment.patient_name,
                patient_age=appointment.patient_age,
                issue=appointment.issue,
                appointment_date=appointment.appointment_date.strftime("%Y-%m-%d"),
                appointment_time=appointment.appointment_time,
                status=appointment.status,
                created_at=appointment.created_at
            ))
        
        return result
        
    except Exception as e:
        logger.error(f"Error retrieving appointments: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve appointments")

@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get specific appointment by ID"""
    try:
        appointment = session.exec(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .where(Appointment.user_id == current_user)
        ).first()
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        doctor = session.exec(select(Doctor).where(Doctor.id == appointment.doctor_id)).first()
        doctor_name = doctor.name if doctor else "Unknown Doctor"
        
        return AppointmentResponse(
            id=appointment.id,
            doctor_id=appointment.doctor_id,
            doctor_name=doctor_name,
            patient_name=appointment.patient_name,
            patient_age=appointment.patient_age,
            issue=appointment.issue,
            appointment_date=appointment.appointment_date.strftime("%Y-%m-%d"),
            appointment_time=appointment.appointment_time,
            status=appointment.status,
            created_at=appointment.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving appointment {appointment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve appointment")

@router.put("/{appointment_id}/cancel")
def cancel_appointment(
    appointment_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Cancel an appointment"""
    try:
        appointment = session.exec(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .where(Appointment.user_id == current_user)
        ).first()
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        if appointment.status == "cancelled":
            raise HTTPException(status_code=400, detail="Appointment is already cancelled")
        
        if appointment.status == "completed":
            raise HTTPException(status_code=400, detail="Cannot cancel completed appointment")
        
        # Check if appointment is in the past
        if appointment.appointment_date < date.today():
            raise HTTPException(status_code=400, detail="Cannot cancel past appointment")
        
        appointment.status = "cancelled"
        session.add(appointment)
        session.commit()
        
        logger.info(f"Cancelled appointment {appointment_id} by user {current_user}")
        
        return {"success": True, "message": "Appointment cancelled successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling appointment {appointment_id}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to cancel appointment")

@router.put("/{appointment_id}/status")
def update_appointment_status(
    appointment_id: int,
    status: str,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update appointment status (Admin/Doctor only)"""
    try:
        appointment = session.exec(select(Appointment).where(Appointment.id == appointment_id)).first()
        
        if not appointment:
            raise HTTPException(status_code=404, detail="Appointment not found")
        
        # Validate status
        valid_statuses = ["scheduled", "confirmed", "cancelled", "completed"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        
        appointment.status = status
        session.add(appointment)
        session.commit()
        
        logger.info(f"Updated appointment {appointment_id} status to {status} by user {current_user}")
        
        return {"success": True, "message": f"Appointment status updated to {status}"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment {appointment_id} status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update appointment status")
