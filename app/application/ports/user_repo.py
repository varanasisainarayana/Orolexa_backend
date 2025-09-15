from typing import Protocol, Optional
from datetime import datetime

class UserDto:
    def __init__(self, id: str, name: Optional[str], phone: str, is_verified: bool,
                 profile_image_id: Optional[str], created_at: datetime, updated_at: datetime):
        self.id = id
        self.name = name
        self.phone = phone
        self.is_verified = is_verified
        self.profile_image_id = profile_image_id
        self.created_at = created_at
        self.updated_at = updated_at

class UserRepository(Protocol):
    def get_by_phone(self, phone: str) -> Optional[UserDto]:
        ...

    def get_by_id(self, user_id: str) -> Optional[UserDto]:
        ...

    def mark_verified(self, user_id: str) -> None:
        ...

    def set_profile_image(self, user_id: str, image_id: Optional[str]) -> None:
        ...

    def update_profile_fields(self, user_id: str, name: Optional[str], age: Optional[int], date_of_birth_iso: Optional[str]) -> None:
        ...