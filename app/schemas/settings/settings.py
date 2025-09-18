# app/schemas/settings.py
from pydantic import BaseModel, Field
from typing import Optional

class NotificationSettings(BaseModel):
    push_enabled: bool = True
    email_enabled: bool = False
    sms_enabled: bool = True

class PrivacySettings(BaseModel):
    data_sharing: bool = True
    analytics: bool = True

class PreferenceSettings(BaseModel):
    language: str = "en"
    theme: str = "light"
    auto_sync: bool = True

class AppSettings(BaseModel):
    notifications: NotificationSettings
    privacy: PrivacySettings
    preferences: PreferenceSettings

class UpdateSettingsRequest(BaseModel):
    notifications: Optional[NotificationSettings] = None
    privacy: Optional[PrivacySettings] = None
    preferences: Optional[PreferenceSettings] = None
