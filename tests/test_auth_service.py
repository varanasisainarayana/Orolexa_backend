from datetime import datetime
from typing import Optional

from app.application.services.auth_service import AuthService, OTPProvider
from app.application.ports.user_repo import UserRepository, UserDto

class FakeUserRepo(UserRepository):
    def __init__(self):
        self.users = {
            "+15551234567": UserDto(
                id="user-1",
                name="Alice",
                phone="+15551234567",
                is_verified=False,
                profile_image_id=None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
        }
        self.verified = set()

    def get_by_phone(self, phone: str) -> Optional[UserDto]:
        return self.users.get(phone)

    def get_by_id(self, user_id: str) -> Optional[UserDto]:
        for u in self.users.values():
            if u.id == user_id:
                return u
        return None

    def mark_verified(self, user_id: str) -> None:
        self.verified.add(user_id)

    def set_profile_image(self, user_id: str, image_id: Optional[str]) -> None:
        pass

class FakeOTP(OTPProvider):
    def __init__(self):
        self.sent = []

    def send(self, phone: str) -> str:
        self.sent.append(phone)
        return "sid"

    def verify(self, phone: str, code: str) -> bool:
        return code == "123456"


def test_send_login_otp():
    repo = FakeUserRepo()
    otp = FakeOTP()
    svc = AuthService(user_repo=repo, otp_provider=otp)
    svc.send_login_otp("+15551234567")
    assert otp.sent == ["+15551234567"]


def test_verify_otp_and_issue_marks_verified_and_returns_user_id():
    repo = FakeUserRepo()
    otp = FakeOTP()
    svc = AuthService(user_repo=repo, otp_provider=otp)
    user_id = svc.verify_otp_and_issue("+15551234567")
    assert user_id == "user-1"
    assert "user-1" in repo.verified
