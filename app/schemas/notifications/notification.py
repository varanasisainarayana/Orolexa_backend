# app/schemas/notification.py
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class NotificationBase(BaseModel):
    type: str
    title: str
    message: str
    data: Optional[Dict[str, Any]] = None

class NotificationCreate(NotificationBase):
    pass

class NotificationResponse(NotificationBase):
    id: int
    read: bool
    created_at: datetime

class NotificationFilters(BaseModel):
    type: Optional[str] = None
    read: Optional[bool] = None
    limit: Optional[int] = 50
    offset: Optional[int] = 0
