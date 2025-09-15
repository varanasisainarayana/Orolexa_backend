import os
import io
from typing import Optional, Tuple
from PIL import Image

from .config import settings
from .storage import get_storage


def create_thumbnail(image_path_or_url: str, local_source_path: str = None, thumbnail_size: Optional[Tuple[int, int]] = None) -> Optional[str]:
    if thumbnail_size is None:
        thumbnail_size = settings.THUMBNAIL_SIZE
    try:
        storage = get_storage()
        src_path = local_source_path or image_path_or_url
        with Image.open(src_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=85, optimize=True)
            buf.seek(0)
            return storage.save_bytes("thumbnails", os.path.basename(src_path), buf.read())
    except Exception:
        return None


