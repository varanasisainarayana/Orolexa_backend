# app/services/storage_service.py
import os
import uuid
from typing import Optional, Tuple
from datetime import datetime
import logging
from PIL import Image
import io

from app.core.config import settings

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.upload_dir = settings.UPLOAD_DIR
        self.max_file_size = settings.MAX_FILE_SIZE
        self.allowed_types = settings.ALLOWED_IMAGE_TYPES
        self.thumbnail_size = settings.THUMBNAIL_SIZE
        
        # Create upload directory if it doesn't exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(os.path.join(self.upload_dir, "profiles"), exist_ok=True)
        os.makedirs(os.path.join(self.upload_dir, "thumbnails"), exist_ok=True)

    def save_image(self, image_data: bytes, filename: str, subfolder: str = "") -> Optional[str]:
        """Save image to storage"""
        try:
            # Validate file size
            if len(image_data) > self.max_file_size:
                logger.error(f"File too large: {len(image_data)} bytes")
                return None
            
            # Generate unique filename
            file_id = str(uuid.uuid4())
            file_ext = os.path.splitext(filename)[1]
            new_filename = f"{file_id}{file_ext}"
            
            # Create path
            if subfolder:
                file_path = os.path.join(self.upload_dir, subfolder, new_filename)
            else:
                file_path = os.path.join(self.upload_dir, new_filename)
            
            # Save file
            with open(file_path, 'wb') as f:
                f.write(image_data)
            
            # Return relative URL
            if subfolder:
                return f"/uploads/{subfolder}/{new_filename}"
            else:
                return f"/uploads/{new_filename}"
                
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            return None

    def create_thumbnail(self, image_data: bytes, filename: str) -> Optional[str]:
        """Create thumbnail for image"""
        try:
            # Open image
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary
            if image.mode in ('RGBA', 'LA', 'P'):
                image = image.convert('RGB')
            
            # Create thumbnail
            image.thumbnail(self.thumbnail_size, Image.Resampling.LANCZOS)
            
            # Generate thumbnail filename
            file_id = str(uuid.uuid4())
            file_ext = os.path.splitext(filename)[1]
            thumb_filename = f"{file_id}_thumb{file_ext}"
            thumb_path = os.path.join(self.upload_dir, "thumbnails", thumb_filename)
            
            # Save thumbnail
            image.save(thumb_path, 'JPEG', quality=85)
            
            return f"/uploads/thumbnails/{thumb_filename}"
            
        except Exception as e:
            logger.error(f"Error creating thumbnail: {e}")
            return None

    def delete_image(self, image_url: str) -> bool:
        """Delete image from storage"""
        try:
            # Convert URL to file path
            if image_url.startswith('/uploads/'):
                file_path = os.path.join(self.upload_dir, image_url[9:])  # Remove '/uploads/'
            else:
                file_path = image_url
            
            if os.path.exists(file_path):
                os.remove(file_path)
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error deleting image: {e}")
            return False

    def validate_image(self, image_data: bytes, filename: str) -> Tuple[bool, str]:
        """Validate image data"""
        try:
            # Check file size
            if len(image_data) > self.max_file_size:
                return False, f"File too large. Max size: {self.max_file_size} bytes"
            
            # Check file type
            image = Image.open(io.BytesIO(image_data))
            mime_type = f"image/{image.format.lower()}"
            
            if mime_type not in self.allowed_types:
                return False, f"File type not allowed. Allowed: {', '.join(self.allowed_types)}"
            
            return True, "Valid image"
            
        except Exception as e:
            return False, f"Invalid image: {str(e)}"

    def get_image_info(self, image_data: bytes) -> dict:
        """Get image information"""
        try:
            image = Image.open(io.BytesIO(image_data))
            return {
                "width": image.width,
                "height": image.height,
                "format": image.format,
                "mode": image.mode,
                "size": len(image_data)
            }
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            return {}
