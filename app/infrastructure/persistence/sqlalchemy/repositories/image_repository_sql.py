from typing import Optional
from sqlmodel import Session, select

from .....models import ImageStorage
from .....application.ports.image_repo import ImageRepository
from .....image_storage import (
    save_image_to_database,
    save_base64_image_to_db,
    get_image_from_database,
    delete_image_from_database,
)


class SqlImageRepository(ImageRepository):
    def __init__(self, session: Session):
        self.session = session

    def save_bytes(self, user_id: str, data: bytes, filename: str, content_type: str, image_type: str = "profile") -> str:
        return save_image_to_database(
            session=self.session,
            user_id=user_id,
            image_data=data,
            filename=filename,
            content_type=content_type,
            image_type=image_type,
            thumbnail_size=(200, 200) if image_type == "profile" else None,
        )

    def save_base64(self, user_id: str, base64_data: str, image_type: str = "profile") -> str:
        return save_base64_image_to_db(
            session=self.session,
            base64_data=base64_data,
            user_id=user_id,
            image_type=image_type,
        )

    def get_bytes(self, image_id: str) -> Optional[bytes]:
        record = get_image_from_database(self.session, image_id)
        return record.image_data if record else None

    def delete(self, image_id: str) -> bool:
        return delete_image_from_database(self.session, image_id)


