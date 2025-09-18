# app/models/notification.py
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class Notification(SQLModel, table=True):
    __tablename__ = "notifications"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    type: str
    title: str
    message: str
    read: bool = Field(default=False)
    data: Optional[str] = Field(default=None)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="notifications")
