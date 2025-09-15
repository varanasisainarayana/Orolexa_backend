from dataclasses import dataclass
from typing import Optional
from datetime import datetime
from fastapi import HTTPException

from ..ports.user_repo import UserRepository


@dataclass
class ProfileService:
    user_repo: UserRepository

    def update_profile(self, user_id: str, name: Optional[str], age: Optional[int], date_of_birth: Optional[str]) -> None:
        if age is not None and age < 0:
            raise HTTPException(status_code=400, detail="Invalid age")
        dob_iso = None
        if date_of_birth is not None:
            try:
                # Validate format
                datetime.strptime(date_of_birth, '%Y-%m-%d')
                dob_iso = date_of_birth
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date_of_birth format. Use YYYY-MM-DD")
        self.user_repo.update_profile_fields(user_id, name, age, dob_iso)


