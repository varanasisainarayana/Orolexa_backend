from typing import List, Optional
from sqlmodel import Session, select

from .....models import Appointment, Doctor
from .....application.ports.appointments_repo import (
    AppointmentsRepository,
    AppointmentDto,
    DoctorDto,
)


class SqlAppointmentsRepository(AppointmentsRepository):
    def __init__(self, session: Session):
        self.session = session

    def _appt_to_dto(self, a: Appointment) -> AppointmentDto:
        return AppointmentDto(
            id=a.id,
            user_id=a.user_id,
            doctor_id=a.doctor_id,
            patient_name=a.patient_name,
            patient_age=a.patient_age,
            issue=a.issue,
            appointment_date=a.appointment_date,
            appointment_time=a.appointment_time,
            status=a.status,
            created_at=a.created_at,
        )

    def get_doctor(self, doctor_id: int) -> Optional[DoctorDto]:
        d = self.session.exec(select(Doctor).where(Doctor.id == doctor_id)).first()
        if not d:
            return None
        return DoctorDto(id=d.id, name=d.name, is_available=bool(getattr(d, "is_available", True)))

    def find_conflict(self, doctor_id: int, appointment_date, appointment_time: str) -> bool:
        existing = self.session.exec(
            select(Appointment)
            .where(Appointment.doctor_id == doctor_id)
            .where(Appointment.appointment_date == appointment_date)
            .where(Appointment.appointment_time == appointment_time)
            .where(Appointment.status.in_(["scheduled", "confirmed"]))
        ).first()
        return existing is not None

    def create(self, user_id: str, doctor_id: int, patient_name: str, patient_age: int, issue: str, appointment_date, appointment_time: str) -> AppointmentDto:
        appt = Appointment(
            user_id=user_id,
            doctor_id=doctor_id,
            patient_name=patient_name,
            patient_age=patient_age,
            issue=issue,
            appointment_date=appointment_date,
            appointment_time=appointment_time,
            status="scheduled",
        )
        self.session.add(appt)
        self.session.commit()
        self.session.refresh(appt)
        return self._appt_to_dto(appt)

    def list_for_user(self, user_id: str) -> List[AppointmentDto]:
        rows = self.session.exec(
            select(Appointment)
            .where(Appointment.user_id == user_id)
            .order_by(Appointment.appointment_date.desc(), Appointment.appointment_time.desc())
        ).all()
        return [self._appt_to_dto(r) for r in rows]

    def get_for_user(self, appointment_id: int, user_id: str) -> Optional[AppointmentDto]:
        a = self.session.exec(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .where(Appointment.user_id == user_id)
        ).first()
        return self._appt_to_dto(a) if a else None

    def cancel(self, appointment_id: int, user_id: str) -> None:
        a = self.session.exec(
            select(Appointment)
            .where(Appointment.id == appointment_id)
            .where(Appointment.user_id == user_id)
        ).first()
        if not a:
            return
        a.status = "cancelled"
        self.session.add(a)
        self.session.commit()

    def update_status(self, appointment_id: int, status: str) -> None:
        a = self.session.exec(select(Appointment).where(Appointment.id == appointment_id)).first()
        if not a:
            return
        a.status = status
        self.session.add(a)
        self.session.commit()

    def get_by_id(self, appointment_id: int) -> Optional[AppointmentDto]:
        a = self.session.exec(select(Appointment).where(Appointment.id == appointment_id)).first()
        return self._appt_to_dto(a) if a else None


