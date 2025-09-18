# app/schemas/user.py
from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
import re
import base64
import io
from PIL import Image

class UserResponse(BaseModel):
    id: str
    name: str
    phone: str
    age: Optional[int] = None
    profile_image_url: Optional[str] = None
    date_of_birth: Optional[str] = None
    created_at: datetime
    updated_at: datetime

class UpdateProfileRequest(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=100, description="User's full name")
    age: Optional[int] = Field(None, ge=1, le=120, description="User's age")
    profile_image: Optional[str] = Field(None, description="Profile image (base64 encoded, file path, or data URL)")
    date_of_birth: Optional[str] = Field(None, description="Date of birth in YYYY-MM-DD format")

    @validator('name')
    def validate_name(cls, v):
        if v is not None:
            if not re.match(r'^[a-zA-Z\s\-]+$', v):
                raise ValueError('Name can only contain letters, spaces, and hyphens')
            return v.strip()
        return v

    @validator('age')
    def validate_age(cls, v):
        if v is not None and (v < 1 or v > 120):
            raise ValueError('Age must be between 1 and 120')
        return v

    @validator('date_of_birth')
    def validate_date_of_birth(cls, v):
        if v is not None:
            try:
                dob = datetime.strptime(v, '%Y-%m-%d')
                if dob > datetime.now():
                    raise ValueError('Date of birth cannot be in the future')
                if (datetime.now() - dob).days > 43800:  # 120 years
                    raise ValueError('Date of birth is too far in the past')
            except ValueError as e:
                if 'Date of birth' in str(e):
                    raise e
                raise ValueError('Invalid date format. Use YYYY-MM-DD')
        return v

class UpdateProfileResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class UploadImageRequest(BaseModel):
    image: str = Field(..., description="Base64 encoded image")

    @validator('image')
    def validate_image(cls, v):
        try:
            if v.startswith('data:image/'):
                header, data = v.split(',', 1)
                image_data = base64.b64decode(data)
            else:
                image_data = base64.b64decode(v)
            
            if len(image_data) > 5 * 1024 * 1024:
                raise ValueError('Image size must be less than 5MB')
            
            image = Image.open(io.BytesIO(image_data))
            if image.format not in ['JPEG', 'PNG', 'WEBP']:
                raise ValueError('Image must be JPEG, PNG, or WebP format')
            
        except Exception as e:
            if 'Image' in str(e):
                raise e
            raise ValueError('Invalid image format')
        return v

class UploadImageResponse(BaseModel):
    success: bool
    message: str
    data: Dict[str, Any]

class DeleteImageResponse(BaseModel):
    success: bool
    message: str

class DeleteAccountRequest(BaseModel):
    password_confirmation: str = Field(..., description="Type 'DELETE' to confirm account deletion")
    
    @validator('password_confirmation')
    def validate_confirmation(cls, v):
        if v != 'DELETE':
            raise ValueError('Please type DELETE to confirm account deletion')
        return v

class DeleteAccountResponse(BaseModel):
    success: bool
    message: str
    data: Optional[Dict[str, Any]] = None
