# app/settings.py
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
import logging
import json
from datetime import datetime

from .database import get_session
from .models import UserSettings, User
from .schemas import AppSettings, UpdateSettingsRequest
from .utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/settings", tags=["Settings"])

# Auth scheme
oauth2_scheme = HTTPBearer()

# Dependency to get current user from JWT
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
def get_settings(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Get user's app settings"""
    try:
        # Get or create user settings
        user_settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == current_user)
        ).first()
        
        if not user_settings:
            # Create default settings
            user_settings = UserSettings(
                user_id=current_user,
                notifications='{"push_enabled": true, "email_enabled": false, "sms_enabled": true}',
                privacy='{"data_sharing": true, "analytics": true}',
                preferences='{"language": "en", "theme": "light", "auto_sync": true}'
            )
            session.add(user_settings)
            session.commit()
            session.refresh(user_settings)
        
        # Parse JSON settings
        try:
            notifications = json.loads(user_settings.notifications)
            privacy = json.loads(user_settings.privacy)
            preferences = json.loads(user_settings.preferences)
        except json.JSONDecodeError:
            # Use defaults if JSON is invalid
            notifications = {"push_enabled": True, "email_enabled": False, "sms_enabled": True}
            privacy = {"data_sharing": True, "analytics": True}
            preferences = {"language": "en", "theme": "light", "auto_sync": True}
        
        logger.info(f"Retrieved settings for user {current_user}")
        
        return AppSettings(
            notifications=notifications,
            privacy=privacy,
            preferences=preferences
        )
        
    except Exception as e:
        logger.error(f"Error retrieving settings for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to retrieve settings")

@router.put("/")
def update_settings(
    settings_data: UpdateSettingsRequest,
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Update user's app settings"""
    try:
        # Get or create user settings
        user_settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == current_user)
        ).first()
        
        if not user_settings:
            user_settings = UserSettings(user_id=current_user)
            session.add(user_settings)
        
        # Update notifications settings
        if settings_data.notifications:
            current_notifications = {}
            if user_settings.notifications:
                try:
                    current_notifications = json.loads(user_settings.notifications)
                except json.JSONDecodeError:
                    current_notifications = {}
            
            # Merge with new settings
            current_notifications.update(settings_data.notifications.dict())
            user_settings.notifications = json.dumps(current_notifications)
        
        # Update privacy settings
        if settings_data.privacy:
            current_privacy = {}
            if user_settings.privacy:
                try:
                    current_privacy = json.loads(user_settings.privacy)
                except json.JSONDecodeError:
                    current_privacy = {}
            
            # Merge with new settings
            current_privacy.update(settings_data.privacy.dict())
            user_settings.privacy = json.dumps(current_privacy)
        
        # Update preferences settings
        if settings_data.preferences:
            current_preferences = {}
            if user_settings.preferences:
                try:
                    current_preferences = json.loads(user_settings.preferences)
                except json.JSONDecodeError:
                    current_preferences = {}
            
            # Merge with new settings
            current_preferences.update(settings_data.preferences.dict())
            user_settings.preferences = json.dumps(current_preferences)
        
        # Update timestamp
        user_settings.updated_at = datetime.utcnow()
        
        session.add(user_settings)
        session.commit()
        session.refresh(user_settings)
        
        logger.info(f"Updated settings for user {current_user}")
        
        return {
            "success": True,
            "message": "Settings updated successfully"
        }
        
    except Exception as e:
        logger.error(f"Error updating settings for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to update settings")

@router.post("/reset")
def reset_settings(
    current_user: int = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """Reset user's settings to defaults"""
    try:
        # Get user settings
        user_settings = session.exec(
            select(UserSettings).where(UserSettings.user_id == current_user)
        ).first()
        
        if user_settings:
            # Reset to defaults
            user_settings.notifications = '{"push_enabled": true, "email_enabled": false, "sms_enabled": true}'
            user_settings.privacy = '{"data_sharing": true, "analytics": true}'
            user_settings.preferences = '{"language": "en", "theme": "light", "auto_sync": true}'
            user_settings.updated_at = datetime.utcnow()
            
            session.add(user_settings)
            session.commit()
        else:
            # Create new settings with defaults
            user_settings = UserSettings(
                user_id=current_user,
                notifications='{"push_enabled": true, "email_enabled": false, "sms_enabled": true}',
                privacy='{"data_sharing": true, "analytics": true}',
                preferences='{"language": "en", "theme": "light", "auto_sync": true}'
            )
            session.add(user_settings)
            session.commit()
        
        logger.info(f"Reset settings for user {current_user}")
        
        return {
            "success": True,
            "message": "Settings reset to defaults successfully"
        }
        
    except Exception as e:
        logger.error(f"Error resetting settings for user {current_user}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to reset settings")
