from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import logging
import json
from datetime import datetime

from ..db.session import get_session
from ..db.models.users.settings import UserSettings
from ..db.models.users.user import User
from ..schemas.settings.settings import AppSettings, UpdateSettingsRequest
from ..services.auth import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])

oauth2_scheme = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    try:
        return int(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=401, detail="Invalid token: invalid user ID format")


@router.get("/", response_model=AppSettings)
def get_settings(current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        user_settings = session.exec(select(UserSettings).where(UserSettings.user_id == current_user)).first()
        if not user_settings:
            user_settings = UserSettings(
                user_id=current_user,
                notifications='{"push_enabled": true, "email_enabled": false, "sms_enabled": true}',
                privacy='{"data_sharing": true, "analytics": true}',
                preferences='{"language": "en", "theme": "light", "auto_sync": true}',
            )
            session.add(user_settings)
            session.commit()
            session.refresh(user_settings)
        try:
            notifications = json.loads(user_settings.notifications)
            privacy = json.loads(user_settings.privacy)
            preferences = json.loads(user_settings.preferences)
        except json.JSONDecodeError:
            notifications = {"push_enabled": True, "email_enabled": False, "sms_enabled": True}
            privacy = {"data_sharing": True, "analytics": True}
            preferences = {"language": "en", "theme": "light", "auto_sync": True}
        return AppSettings(notifications=notifications, privacy=privacy, preferences=preferences)
    except Exception as e:
        logger.error(f"Error retrieving settings for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")


@router.put("/")
def update_settings(settings_data: UpdateSettingsRequest, current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        user_settings = session.exec(select(UserSettings).where(UserSettings.user_id == current_user)).first()
        if not user_settings:
            user_settings = UserSettings(user_id=current_user)
            session.add(user_settings)
        if settings_data.notifications:
            current_notifications = {}
            if user_settings.notifications:
                try:
                    current_notifications = json.loads(user_settings.notifications)
                except json.JSONDecodeError:
                    current_notifications = {}
            current_notifications.update(settings_data.notifications.dict())
            user_settings.notifications = json.dumps(current_notifications)
        if settings_data.privacy:
            current_privacy = {}
            if user_settings.privacy:
                try:
                    current_privacy = json.loads(user_settings.privacy)
                except json.JSONDecodeError:
                    current_privacy = {}
            current_privacy.update(settings_data.privacy.dict())
            user_settings.privacy = json.dumps(current_privacy)
        if settings_data.preferences:
            current_preferences = {}
            if user_settings.preferences:
                try:
                    current_preferences = json.loads(user_settings.preferences)
                except json.JSONDecodeError:
                    current_preferences = {}
            current_preferences.update(settings_data.preferences.dict())
            user_settings.preferences = json.dumps(current_preferences)
        user_settings.updated_at = datetime.utcnow()
        session.add(user_settings)
        session.commit()
        session.refresh(user_settings)
        return {"success": True, "message": "Settings updated successfully"}
    except Exception as e:
        logger.error(f"Error updating settings for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update settings")


@router.post("/reset")
def reset_settings(current_user: int = Depends(get_current_user), session: Session = Depends(get_session)):
    try:
        user_settings = session.exec(select(UserSettings).where(UserSettings.user_id == current_user)).first()
        if user_settings:
            user_settings.notifications = '{"push_enabled": true, "email_enabled": false, "sms_enabled": true}'
            user_settings.privacy = '{"data_sharing": true, "analytics": true}'
            user_settings.preferences = '{"language": "en", "theme": "light", "auto_sync": true}'
            user_settings.updated_at = datetime.utcnow()
            session.add(user_settings)
            session.commit()
        else:
            user_settings = UserSettings(
                user_id=current_user,
                notifications='{"push_enabled": true, "email_enabled": false, "sms_enabled": true}',
                privacy='{"data_sharing": true, "analytics": true}',
                preferences='{"language": "en", "theme": "light", "auto_sync": true}',
            )
            session.add(user_settings)
            session.commit()
        return {"success": True, "message": "Settings reset to defaults successfully"}
    except Exception as e:
        logger.error(f"Error resetting settings for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset settings")


