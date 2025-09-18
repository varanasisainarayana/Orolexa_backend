# app/services/analysis_service.py
from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime
import logging

from app.db.models import AnalysisHistory
from app.schemas import AnalysisResponse

logger = logging.getLogger(__name__)

class AnalysisService:
    def __init__(self, session: Session):
        self.session = session

    def create_analysis(self, user_id: str, image_url: str, ai_report: str, doctor_name: str = "Dr. AI Assistant") -> Optional[AnalysisHistory]:
        """Create new analysis record"""
        try:
            analysis = AnalysisHistory(
                user_id=user_id,
                image_url=image_url,
                ai_report=ai_report,
                doctor_name=doctor_name,
                status="completed"
            )
            self.session.add(analysis)
            self.session.commit()
            self.session.refresh(analysis)
            return analysis
        except Exception as e:
            logger.error(f"Error creating analysis: {e}")
            self.session.rollback()
            return None

    def get_analysis_by_id(self, analysis_id: int) -> Optional[AnalysisHistory]:
        """Get analysis by ID"""
        try:
            return self.session.exec(select(AnalysisHistory).where(AnalysisHistory.id == analysis_id)).first()
        except Exception as e:
            logger.error(f"Error getting analysis {analysis_id}: {e}")
            return None

    def get_user_analyses(self, user_id: str, skip: int = 0, limit: int = 100) -> List[AnalysisHistory]:
        """Get user's analysis history"""
        try:
            return self.session.exec(
                select(AnalysisHistory)
                .where(AnalysisHistory.user_id == user_id)
                .offset(skip)
                .limit(limit)
                .order_by(AnalysisHistory.created_at.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting user analyses: {e}")
            return []

    def update_analysis_status(self, analysis_id: int, status: str) -> bool:
        """Update analysis status"""
        try:
            analysis = self.get_analysis_by_id(analysis_id)
            if not analysis:
                return False
            
            analysis.status = status
            self.session.add(analysis)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error updating analysis status: {e}")
            self.session.rollback()
            return False

    def delete_analysis(self, analysis_id: int) -> bool:
        """Delete analysis"""
        try:
            analysis = self.get_analysis_by_id(analysis_id)
            if not analysis:
                return False
            
            self.session.delete(analysis)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting analysis: {e}")
            self.session.rollback()
            return False

    def get_recent_analyses(self, user_id: str, days: int = 30) -> List[AnalysisHistory]:
        """Get recent analyses within specified days"""
        try:
            from datetime import timedelta
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            return self.session.exec(
                select(AnalysisHistory)
                .where(
                    AnalysisHistory.user_id == user_id,
                    AnalysisHistory.created_at >= cutoff_date
                )
                .order_by(AnalysisHistory.created_at.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting recent analyses: {e}")
            return []
