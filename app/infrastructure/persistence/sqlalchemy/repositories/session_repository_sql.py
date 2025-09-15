from datetime import datetime
from sqlmodel import Session

from .....models import UserSession
from .....application.ports.session_repo import SessionRepository, SessionDto


class SqlSessionRepository(SessionRepository):
    def __init__(self, session: Session):
        self.session = session

    def create(self, user_id: str, token: str, refresh_token: str, expires_at: datetime) -> SessionDto:
        rec = UserSession(user_id=user_id, token=token, refresh_token=refresh_token, expires_at=expires_at)
        self.session.add(rec)
        self.session.commit()
        self.session.refresh(rec)
        return SessionDto(
            id=rec.id,
            user_id=rec.user_id,
            token=rec.token,
            refresh_token=rec.refresh_token,
            expires_at=rec.expires_at,
            created_at=rec.created_at,
        )


