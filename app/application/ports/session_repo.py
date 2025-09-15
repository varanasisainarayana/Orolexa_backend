from dataclasses import dataclass
from datetime import datetime


@dataclass
class SessionDto:
    id: str
    user_id: str
    token: str
    refresh_token: str
    expires_at: datetime
    created_at: datetime


class SessionRepository:
    def create(self, user_id: str, token: str, refresh_token: str, expires_at: datetime) -> SessionDto:
        ...


