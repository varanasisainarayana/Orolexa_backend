from typing import Optional
from sqlmodel import Session, select

from .....models import User
from .....application.ports.user_repo import UserRepository, UserDto

class SqlUserRepository(UserRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_dto(self, user: User) -> UserDto:
        return UserDto(
            id=user.id,
            name=getattr(user, 'name', None),
            phone=user.phone,
            is_verified=bool(getattr(user, 'is_verified', False)),
            profile_image_id=getattr(user, 'profile_image_id', None),
            created_at=user.created_at,
            updated_at=user.updated_at,
        )

    def get_by_phone(self, phone: str) -> Optional[UserDto]:
        user = self.session.exec(select(User).where(User.phone == phone)).first()
        return self._to_dto(user) if user else None

    def get_by_id(self, user_id: str) -> Optional[UserDto]:
        user = self.session.exec(select(User).where(User.id == user_id)).first()
        return self._to_dto(user) if user else None

    def mark_verified(self, user_id: str) -> None:
        user = self.session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            return
        user.is_verified = True
        self.session.add(user)
        self.session.commit()

    def set_profile_image(self, user_id: str, image_id: Optional[str]) -> None:
        user = self.session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            return
        user.profile_image_id = image_id
        self.session.add(user)
        self.session.commit()

    def update_profile_fields(self, user_id: str, name: Optional[str], age: Optional[int], date_of_birth_iso: Optional[str]) -> None:
        user = self.session.exec(select(User).where(User.id == user_id)).first()
        if not user:
            return
        if name is not None:
            user.name = name
        if age is not None:
            user.age = age
        if date_of_birth_iso is not None:
            from datetime import datetime as _dt
            user.date_of_birth = _dt.strptime(date_of_birth_iso, '%Y-%m-%d')
        self.session.add(user)
        self.session.commit()