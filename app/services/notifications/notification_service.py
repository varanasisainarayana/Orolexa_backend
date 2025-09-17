# app/services/notification_service.py
from typing import List, Optional
from sqlmodel import Session, select
from datetime import datetime
import logging

from app.db.models import Notification
from app.schemas import NotificationCreate, NotificationFilters

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, session: Session):
        self.session = session

    def create_notification(self, notification_data: NotificationCreate, user_id: str) -> Optional[Notification]:
        """Create new notification"""
        try:
            notification = Notification(
                user_id=user_id,
                **notification_data.dict()
            )
            self.session.add(notification)
            self.session.commit()
            self.session.refresh(notification)
            return notification
        except Exception as e:
            logger.error(f"Error creating notification: {e}")
            self.session.rollback()
            return None

    def get_notification_by_id(self, notification_id: int) -> Optional[Notification]:
        """Get notification by ID"""
        try:
            return self.session.exec(select(Notification).where(Notification.id == notification_id)).first()
        except Exception as e:
            logger.error(f"Error getting notification {notification_id}: {e}")
            return None

    def get_user_notifications(self, user_id: str, filters: NotificationFilters = None) -> List[Notification]:
        """Get user's notifications with optional filters"""
        try:
            query = select(Notification).where(Notification.user_id == user_id)
            
            if filters:
                if filters.type:
                    query = query.where(Notification.type == filters.type)
                if filters.read is not None:
                    query = query.where(Notification.read == filters.read)
            
            return self.session.exec(
                query
                .offset(filters.offset if filters else 0)
                .limit(filters.limit if filters else 50)
                .order_by(Notification.created_at.desc())
            ).all()
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []

    def mark_as_read(self, notification_id: int) -> bool:
        """Mark notification as read"""
        try:
            notification = self.get_notification_by_id(notification_id)
            if not notification:
                return False
            
            notification.read = True
            self.session.add(notification)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            self.session.rollback()
            return False

    def mark_all_as_read(self, user_id: str) -> int:
        """Mark all user notifications as read"""
        try:
            notifications = self.session.exec(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.read == False
                )
            ).all()
            
            count = 0
            for notification in notifications:
                notification.read = True
                self.session.add(notification)
                count += 1
            
            self.session.commit()
            return count
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            self.session.rollback()
            return 0

    def delete_notification(self, notification_id: int) -> bool:
        """Delete notification"""
        try:
            notification = self.get_notification_by_id(notification_id)
            if not notification:
                return False
            
            self.session.delete(notification)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error deleting notification: {e}")
            self.session.rollback()
            return False

    def get_unread_count(self, user_id: str) -> int:
        """Get unread notification count for user"""
        try:
            count = self.session.exec(
                select(Notification).where(
                    Notification.user_id == user_id,
                    Notification.read == False
                )
            ).count()
            return count
        except Exception as e:
            logger.error(f"Error getting unread count: {e}")
            return 0
