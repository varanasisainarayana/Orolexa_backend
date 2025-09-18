# app/models/device.py
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class DeviceConnection(SQLModel, table=True):
    __tablename__ = "device_connections"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    device_id: str
    device_name: str
    ip_address: Optional[str] = None
    connected_at: datetime = Field(default_factory=datetime.utcnow)
    disconnected_at: Optional[datetime] = None
    is_active: bool = Field(default=True)
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="device_connections")
