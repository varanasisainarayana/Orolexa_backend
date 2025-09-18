# app/schemas/device.py
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class DeviceConnectionBase(BaseModel):
    device_id: str
    device_name: str
    ip_address: Optional[str] = None

class DeviceConnectionCreate(DeviceConnectionBase):
    pass

class DeviceConnectionResponse(DeviceConnectionBase):
    id: int
    connected_at: datetime
    disconnected_at: Optional[datetime] = None
    is_active: bool

class DeviceStatus(BaseModel):
    connected: bool
    device_id: Optional[str] = None
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    last_seen: Optional[datetime] = None
    battery_level: Optional[int] = None
    firmware_version: Optional[str] = None
