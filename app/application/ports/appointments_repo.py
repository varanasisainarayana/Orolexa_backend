from dataclasses import dataclass
from typing import List, Optional
from datetime import datetime, date


@dataclass
class DoctorDto:
    id: int
    name: str
    is_available: bool


@dataclass
class AppointmentDto:
    id: int
    user_id: str
    doctor_id: int
    patient_name: str
    patient_age: int
    issue: str
    appointment_date: date
    appointment_time: str
    status: str
    created_at: datetime


class AppointmentsRepository:
    def get_doctor(self, doctor_id: int) -> Optional[DoctorDto]:
        ...

    def find_conflict(self, doctor_id: int, appointment_date: date, appointment_time: str) -> bool:
        ...

    def create(self, user_id: str, doctor_id: int, patient_name: str, patient_age: int, issue: str, appointment_date: date, appointment_time: str) -> AppointmentDto:
        ...

    def list_for_user(self, user_id: str) -> List[AppointmentDto]:
        ...

    def get_for_user(self, appointment_id: int, user_id: str) -> Optional[AppointmentDto]:
        ...

    def cancel(self, appointment_id: int, user_id: str) -> None:
        ...

    def update_status(self, appointment_id: int, status: str) -> None:
        ...

    def get_by_id(self, appointment_id: int) -> Optional[AppointmentDto]:
        ...


