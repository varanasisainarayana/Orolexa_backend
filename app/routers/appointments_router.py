from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import logging
from datetime import datetime, date

from ..db.session import get_session
from ..db.models.health.appointment import Appointment
from ..db.models.health.doctor import Doctor
from ..db.models.users.user import User
from ..schemas.appointments.appointment import AppointmentCreate, AppointmentResponse
from ..services.appointments.appointment_service import AppointmentService
from ..services.auth import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/appointments", tags=["Appointments"])

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


def get_appointments_service(session: Session = Depends(get_session)) -> AppointmentService:
    return AppointmentService(session)


@router.post("/", response_model=AppointmentResponse)
def book_appointment(
    appointment_data: AppointmentCreate,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session),
    appt_service: AppointmentService = Depends(get_appointments_service),
):
    try:
        appt = appt_service.create_appointment(appointment_data, user_id=str(current_user))
        doctor = session.exec(select(Doctor).where(Doctor.id == appt.doctor_id)).first()
        doctor_name = doctor.name if doctor else "Unknown Doctor"
        return AppointmentResponse(
            id=appt.id,
            doctor_id=appt.doctor_id,
            doctor_name=doctor_name,
            patient_name=appt.patient_name,
            patient_age=appt.patient_age,
            issue=appt.issue,
            appointment_date=appt.appointment_date.strftime("%Y-%m-%d"),
            appointment_time=appt.appointment_time,
            status=appt.status,
            created_at=appt.created_at,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error booking appointment: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to book appointment")


@router.get("/", response_model=List[AppointmentResponse])
def get_user_appointments(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session),
    appt_service: AppointmentService = Depends(get_appointments_service),
):
    try:
        appts = appt_service.get_user_appointments(str(current_user))
        result = []
        for a in appts:
            doctor = session.exec(select(Doctor).where(Doctor.id == a.doctor_id)).first()
            doctor_name = doctor.name if doctor else "Unknown Doctor"
            result.append(
                AppointmentResponse(
                    id=a.id,
                    doctor_id=a.doctor_id,
                    doctor_name=doctor_name,
                    patient_name=a.patient_name,
                    patient_age=a.patient_age,
                    issue=a.issue,
                    appointment_date=a.appointment_date.strftime("%Y-%m-%d"),
                    appointment_time=a.appointment_time,
                    status=a.status,
                    created_at=a.created_at,
                )
            )
        return result
    except Exception as e:
        logger.error(f"Error retrieving appointments: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve appointments")


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session),
    appt_service: AppointmentService = Depends(get_appointments_service),
):
    try:
        a = appt_service.get_appointment_by_id(appointment_id)
        if not a or str(a.user_id) != str(current_user):
            raise HTTPException(status_code=404, detail="Appointment not found")
        doctor = session.exec(select(Doctor).where(Doctor.id == a.doctor_id)).first()
        doctor_name = doctor.name if doctor else "Unknown Doctor"
        return AppointmentResponse(
            id=a.id,
            doctor_id=a.doctor_id,
            doctor_name=doctor_name,
            patient_name=a.patient_name,
            patient_age=a.patient_age,
            issue=a.issue,
            appointment_date=a.appointment_date.strftime("%Y-%m-%d"),
            appointment_time=a.appointment_time,
            status=a.status,
            created_at=a.created_at,
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
    session: Session = Depends(get_session),
    appt_service: AppointmentService = Depends(get_appointments_service),
):
    try:
        # Mark appointment as cancelled
        ok = appt_service.update_appointment_status(appointment_id, "cancelled")
        if not ok:
            raise HTTPException(status_code=404, detail="Appointment not found")
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
    session: Session = Depends(get_session),
    appt_service: AppointmentService = Depends(get_appointments_service),
):
    try:
        ok = appt_service.update_appointment_status(appointment_id, status)
        if not ok:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return {"success": True, "message": f"Appointment status updated to {status}"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating appointment {appointment_id} status: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update appointment status")


