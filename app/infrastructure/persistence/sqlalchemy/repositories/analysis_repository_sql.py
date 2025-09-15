from typing import List, Optional
from sqlmodel import Session, select

from .....models import AnalysisHistory
from .....application.ports.analysis_repo import AnalysisRepository, AnalysisRecord


class SqlAnalysisRepository(AnalysisRepository):
    def __init__(self, session: Session):
        self.session = session

    def _to_record(self, h: AnalysisHistory) -> AnalysisRecord:
        return AnalysisRecord(
            id=h.id,
            user_id=h.user_id,
            image_url=h.image_url,
            ai_report=h.ai_report,
            thumbnail_url=h.thumbnail_url,
            created_at=h.created_at,
        )

    def create(self, user_id: str, image_url: str, ai_report: str, thumbnail_url: Optional[str]) -> AnalysisRecord:
        entry = AnalysisHistory(
            user_id=user_id,
            image_url=image_url,
            ai_report=ai_report,
            doctor_name="Dr. AI Assistant",
            status="completed",
            thumbnail_url=thumbnail_url,
        )
        self.session.add(entry)
        self.session.commit()
        self.session.refresh(entry)
        return self._to_record(entry)

    def list_for_user(self, user_id: str) -> List[AnalysisRecord]:
        rows = self.session.exec(
            select(AnalysisHistory)
            .where(AnalysisHistory.user_id == user_id)
            .order_by(AnalysisHistory.created_at.desc())
        ).all()
        return [self._to_record(r) for r in rows]


