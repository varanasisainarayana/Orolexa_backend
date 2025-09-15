# app/image_storage.py
import os
import uuid
from typing import Optional, Tuple
from fastapi import HTTPException, UploadFile
from sqlmodel import Session, select
from PIL import Image
import io
import base64
from .models import ImageStorage, User
from .config import settings
import logging

logger = logging.getLogger(__name__)

def save_image_to_database(
    session: Session,
    user_id: str,
    image_data: bytes,
    filename: str,
    content_type: str,
    image_type: str = "profile",
    thumbnail_size: Optional[Tuple[int, int]] = None
) -> str:
    """
    Save image data to database and return the image ID
    """
    try:
        # Get image dimensions if possible
        width, height = None, None
        try:
            with Image.open(io.BytesIO(image_data)) as img:
                width, height = img.size
        except Exception as e:
            logger.warning(f"Could not get image dimensions: {e}")
        
        # Create thumbnail if requested
        thumbnail_id = None
        if thumbnail_size and content_type.startswith('image/'):
            try:
                thumbnail_data = create_thumbnail_from_bytes(image_data, thumbnail_size)
                if thumbnail_data:
                    thumbnail_id = save_image_to_database(
                        session, user_id, thumbnail_data, 
                        f"thumb_{filename}", content_type, "thumbnail"
                    )
            except Exception as e:
                logger.warning(f"Could not create thumbnail: {e}")
        
        # Create image storage record
        image_record = ImageStorage(
            user_id=user_id,
            filename=filename,
            content_type=content_type,
            file_size=len(image_data),
            image_data=image_data,
            image_type=image_type,
            width=width,
            height=height,
            thumbnail_id=thumbnail_id
        )
        
        session.add(image_record)
        session.commit()
        session.refresh(image_record)
        
        logger.info(f"Image saved to database with ID: {image_record.id}")
        return image_record.id
        
    except Exception as e:
        logger.error(f"Error saving image to database: {e}")
        session.rollback()
        raise HTTPException(status_code=500, detail="Failed to save image to database")

def get_image_from_database(session: Session, image_id: str) -> Optional[ImageStorage]:
    """
    Retrieve image data from database
    """
    try:
        image_record = session.exec(
            select(ImageStorage).where(ImageStorage.id == image_id)
        ).first()
        return image_record
    except Exception as e:
        logger.error(f"Error retrieving image from database: {e}")
        return None

def create_thumbnail_from_bytes(image_data: bytes, size: Tuple[int, int]) -> Optional[bytes]:
    """
    Create thumbnail from image bytes
    """
    try:
        with Image.open(io.BytesIO(image_data)) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Create thumbnail
            img.thumbnail(size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            return output.getvalue()
    except Exception as e:
        logger.error(f"Error creating thumbnail: {e}")
        return None

def save_uploaded_file_to_db(session: Session, file: UploadFile, user_id: str, image_type: str = "profile") -> str:
    """
    Save uploaded file to database
    """
    try:
        # Read file data
        file_data = file.file.read()
        file.file.seek(0)  # Reset file pointer
        
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1] if file.filename else '.jpg'
        filename = f"{uuid.uuid4()}{file_extension}"
        
        # Save to database
        image_id = save_image_to_database(
            session=session,
            user_id=user_id,
            image_data=file_data,
            filename=filename,
            content_type=file.content_type or 'image/jpeg',
            image_type=image_type,
            thumbnail_size=(200, 200) if image_type == "profile" else None
        )
        
        return image_id
        
    except Exception as e:
        logger.error(f"Error saving uploaded file to database: {e}")
        raise HTTPException(status_code=500, detail="Failed to save uploaded file")

def save_base64_image_to_db(session: Session, base64_data: str, user_id: str, image_type: str = "profile") -> str:
    """
    Save base64 encoded image to database
    """
    try:
        # Handle data URL format
        if ',' in base64_data:
            header, data = base64_data.split(',', 1)
            content_type = header.split(':')[1].split(';')[0] if ':' in header else 'image/jpeg'
        else:
            data = base64_data
            content_type = 'image/jpeg'
        
        # Decode base64
        image_data = base64.b64decode(data)
        
        # Generate filename
        file_extension = '.jpg'
        if 'png' in content_type:
            file_extension = '.png'
        elif 'webp' in content_type:
            file_extension = '.webp'
        
        filename = f"{uuid.uuid4()}{file_extension}"
        
        # Save to database
        image_id = save_image_to_database(
            session=session,
            user_id=user_id,
            image_data=image_data,
            filename=filename,
            content_type=content_type,
            image_type=image_type,
            thumbnail_size=(200, 200) if image_type == "profile" else None
        )
        
        return image_id
        
    except Exception as e:
        logger.error(f"Error saving base64 image to database: {e}")
        raise HTTPException(status_code=500, detail="Failed to save base64 image")

def delete_image_from_database(session: Session, image_id: str) -> bool:
    """
    Delete image from database
    """
    try:
        image_record = session.exec(
            select(ImageStorage).where(ImageStorage.id == image_id)
        ).first()
        
        if not image_record:
            return False
        
        # Delete thumbnail if exists
        if image_record.thumbnail_id:
            delete_image_from_database(session, image_record.thumbnail_id)
        
        session.delete(image_record)
        session.commit()
        
        logger.info(f"Image {image_id} deleted from database")
        return True
        
    except Exception as e:
        logger.error(f"Error deleting image from database: {e}")
        session.rollback()
        return False

def get_user_profile_image(session: Session, user_id: str) -> Optional[ImageStorage]:
    """
    Get user's profile image from database
    """
    try:
        user = session.exec(
            select(User).where(User.id == user_id)
        ).first()
        
        if not user or not user.profile_image_id:
            return None
        
        return get_image_from_database(session, user.profile_image_id)
        
    except Exception as e:
        logger.error(f"Error getting user profile image: {e}")
        return None
