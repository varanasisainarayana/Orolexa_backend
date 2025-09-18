# app/models/image.py
from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime
import uuid
from sqlalchemy import Column, LargeBinary

class ImageStorage(SQLModel, table=True):
    __tablename__ = "image_storage"
    id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True)
    user_id: str = Field(foreign_key="users.id", index=True)
    filename: str = Field(max_length=255)
    content_type: str = Field(max_length=100)
    file_size: int
    image_data: bytes = Field(sa_column=Column(LargeBinary))
    image_type: str = Field(max_length=50)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    width: Optional[int] = None
    height: Optional[int] = None
    thumbnail_id: Optional[str] = Field(foreign_key="image_storage.id", default=None)
