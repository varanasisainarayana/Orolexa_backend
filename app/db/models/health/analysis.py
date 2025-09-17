# app/models/analysis.py
from typing import Optional
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime

class AnalysisHistory(SQLModel, table=True):
    __tablename__ = "analysis_history"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: str = Field(foreign_key="users.id")
    image_url: str
    ai_report: str
    doctor_name: Optional[str] = Field(default="Dr. AI Assistant")
    status: str = Field(default="completed")
    thumbnail_url: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    # Relationships
    user: Optional["User"] = Relationship(back_populates="histories")
