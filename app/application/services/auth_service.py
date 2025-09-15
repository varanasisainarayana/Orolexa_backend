from typing import Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from ..ports.user_repo import UserRepository, UserDto
from ..ports.session_repo import SessionRepository
from ..ports.otp_provider import OTPProvider

@dataclass
class AuthService:
    user_repo: UserRepository
    otp_provider: OTPProvider
    session_repo: SessionRepository | None = None

    def send_login_otp(self, phone: str) -> None:
        self.otp_provider.send(phone)

    def verify_otp_and_issue(self, phone: str) -> Optional[str]:
        user = self.user_repo.get_by_phone(phone)
        if not user:
            return None
        self.user_repo.mark_verified(user.id)
        return user.id
