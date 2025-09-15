from dataclasses import dataclass
from typing import List
from datetime import datetime, date
from fastapi import HTTPException

from ..ports.appointments_repo import AppointmentsRepository, AppointmentDto
from ..ports.user_repo import UserRepository


@dataclass
class AppointmentsService:
    repo: AppointmentsRepository
    user_repo: UserRepository

    def book(self, user_id: str, doctor_id: int, patient_name: str, patient_age: int, issue: str, appointment_date_str: str, appointment_time: str) -> AppointmentDto:
        try:
            appointment_date = datetime.strptime(appointment_date_str, "%Y-%m-%d").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid appointment date format. Use YYYY-MM-DD")

        if appointment_date < date.today():
            raise HTTPException(status_code=400, detail="Appointment date cannot be in the past")

        try:
            datetime.strptime(appointment_time, "%H:%M")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid appointment time format. Use HH:MM")

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        doctor = self.repo.get_doctor(doctor_id)
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor not found")
        if not doctor.is_available:
            raise HTTPException(status_code=400, detail="Doctor is not available")

        if self.repo.find_conflict(doctor_id, appointment_date, appointment_time):
            raise HTTPException(status_code=400, detail="This time slot is already booked")

        return self.repo.create(user_id, doctor_id, patient_name, patient_age, issue, appointment_date, appointment_time)

    def list_for_user(self, user_id: str) -> List[AppointmentDto]:
        return self.repo.list_for_user(user_id)

    def get_for_user(self, user_id: str, appointment_id: int) -> AppointmentDto:
        appt = self.repo.get_for_user(appointment_id, user_id)
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found")
        return appt

    def cancel(self, user_id: str, appointment_id: int) -> None:
        appt = self.repo.get_for_user(appointment_id, user_id)
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found")
        if appt.status == "cancelled":
            raise HTTPException(status_code=400, detail="Appointment is already cancelled")
        if appt.status == "completed":
            raise HTTPException(status_code=400, detail="Cannot cancel completed appointment")
        if appt.appointment_date < date.today():
            raise HTTPException(status_code=400, detail="Cannot cancel past appointment")
        self.repo.cancel(appointment_id, user_id)

    def update_status(self, appointment_id: int, status: str) -> None:
        valid_statuses = ["scheduled", "confirmed", "cancelled", "completed"]
        if status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")
        if not self.repo.get_by_id(appointment_id):
            raise HTTPException(status_code=404, detail="Appointment not found")
        self.repo.update_status(appointment_id, status)


