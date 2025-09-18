# app/models/session.py
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
import uuid

class UserSession(SQLModel, table=True):
    __tablename__ = "user_sessions"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    token: str = Field(max_length=500, index=True)
    refresh_token: str = Field(max_length=500, index=True)
    device_info: Optional[str] = Field(default=None)
    ip_address: Optional[str] = Field(max_length=45, default=None)
    expires_at: datetime
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="sessions")
