# app/services/settings_service.py
from typing import Optional
from sqlmodel import Session, select
from datetime import datetime
import json
import logging

from app.db.models import UserSettings
from app.schemas import AppSettings, UpdateSettingsRequest

logger = logging.getLogger(__name__)

class SettingsService:
    def __init__(self, session: Session):
        self.session = session

    def get_user_settings(self, user_id: str) -> Optional[UserSettings]:
        """Get user settings"""
        try:
            return self.session.exec(select(UserSettings).where(UserSettings.user_id == user_id)).first()
        except Exception as e:
            logger.error(f"Error getting user settings: {e}")
            return None

    def create_user_settings(self, user_id: str) -> Optional[UserSettings]:
        """Create default user settings"""
        try:
            settings = UserSettings(user_id=user_id)
            self.session.add(settings)
            self.session.commit()
            self.session.refresh(settings)
            return settings
        except Exception as e:
            logger.error(f"Error creating user settings: {e}")
            self.session.rollback()
            return None

    def update_user_settings(self, user_id: str, update_data: UpdateSettingsRequest) -> Optional[UserSettings]:
        """Update user settings"""
        try:
            settings = self.get_user_settings(user_id)
            if not settings:
                settings = self.create_user_settings(user_id)
                if not settings:
                    return None
            
            if update_data.notifications:
                settings.notifications = update_data.notifications.json()
            
            if update_data.privacy:
                settings.privacy = update_data.privacy.json()
            
            if update_data.preferences:
                settings.preferences = update_data.preferences.json()
            
            settings.updated_at = datetime.utcnow()
            self.session.add(settings)
            self.session.commit()
            self.session.refresh(settings)
            return settings
        except Exception as e:
            logger.error(f"Error updating user settings: {e}")
            self.session.rollback()
            return None

    def get_app_settings(self, user_id: str) -> Optional[AppSettings]:
        """Get app settings as structured object"""
        try:
            settings = self.get_user_settings(user_id)
            if not settings:
                return None
            
            return AppSettings(
                notifications=json.loads(settings.notifications),
                privacy=json.loads(settings.privacy),
                preferences=json.loads(settings.preferences)
            )
        except Exception as e:
            logger.error(f"Error getting app settings: {e}")
            return None

    def reset_to_defaults(self, user_id: str) -> bool:
        """Reset user settings to defaults"""
        try:
            settings = self.get_user_settings(user_id)
            if not settings:
                return False
            
            settings.notifications = '{"push_enabled": true, "email_enabled": false, "sms_enabled": true}'
            settings.privacy = '{"data_sharing": true, "analytics": true}'
            settings.preferences = '{"language": "en", "theme": "light", "auto_sync": true}'
            settings.updated_at = datetime.utcnow()
            
            self.session.add(settings)
            self.session.commit()
            return True
        except Exception as e:
            logger.error(f"Error resetting settings to defaults: {e}")
            self.session.rollback()
            return False
