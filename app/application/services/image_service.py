from typing import Optional
from dataclasses import dataclass
from fastapi import UploadFile, HTTPException

from ..ports.image_repo import ImageRepository
from ..ports.user_repo import UserRepository


@dataclass
class ImageService:
    image_repo: ImageRepository
    user_repo: UserRepository

    def upload_profile_file(self, user_id: str, file: UploadFile) -> str:
        file_data = file.file.read()
        file.file.seek(0)
        filename = file.filename or "upload.jpg"
        content_type = file.content_type or "image/jpeg"
        image_id = self.image_repo.save_bytes(user_id, file_data, filename, content_type, image_type="profile")
        self.user_repo.set_profile_image(user_id, image_id)
        return image_id

    def upload_profile_base64(self, user_id: str, base64_data: str) -> str:
        image_id = self.image_repo.save_base64(user_id, base64_data, image_type="profile")
        self.user_repo.set_profile_image(user_id, image_id)
        return image_id

    def delete_profile_image(self, user_id: str) -> None:
        user = self.user_repo.get_by_id(user_id)
        if not user or not user.profile_image_id:
            return
        self.image_repo.delete(user.profile_image_id)
        self.user_repo.set_profile_image(user_id, None)


