from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class AnalysisRecord:
    id: int
    user_id: str
    image_url: str
    ai_report: str
    thumbnail_url: Optional[str]
    created_at: datetime


class AnalysisRepository:
    def create(self, user_id: str, image_url: str, ai_report: str, thumbnail_url: Optional[str]) -> AnalysisRecord:
        ...

    def list_for_user(self, user_id: str) -> List[AnalysisRecord]:
        ...


