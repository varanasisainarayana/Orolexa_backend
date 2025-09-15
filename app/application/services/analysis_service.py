from dataclasses import dataclass
from typing import List, Optional
from fastapi import UploadFile, HTTPException
import mimetypes

from ..ports.analysis_repo import AnalysisRepository, AnalysisRecord
from ..ports.user_repo import UserRepository
from ..ports.ai_provider import AIProvider
from ..ports.storage_repo import StorageRepository
from ...config import settings
from ...media_utils import create_thumbnail  # reuse utility without circular import


@dataclass
class AnalysisService:
    analysis_repo: AnalysisRepository
    user_repo: UserRepository
    ai_provider: AIProvider
    storage_repo: StorageRepository

    async def analyze_images(self, user_id: str, files: List[UploadFile], prompt: str) -> List[AnalysisRecord]:
        if not files:
            raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

        user = self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        created: List[AnalysisRecord] = []

        for uploaded in files:
            if uploaded.content_type not in settings.ALLOWED_IMAGE_TYPES:
                raise HTTPException(status_code=415, detail=f"File type {uploaded.content_type} not allowed")

            uploaded.file.seek(0, 2)
            file_size = uploaded.file.tell()
            uploaded.file.seek(0)
            if file_size > settings.MAX_FILE_SIZE:
                raise HTTPException(status_code=413, detail=f"File too large (max {settings.MAX_FILE_SIZE // (1024*1024)}MB)")

            tmp_dir = settings.UPLOAD_DIR
            import os
            from datetime import datetime
            os.makedirs(tmp_dir, exist_ok=True)
            local_tmp_path = os.path.join(tmp_dir, f"{int(datetime.utcnow().timestamp()*1000)}_{uploaded.filename}")
            with open(local_tmp_path, "wb") as f:
                content = await uploaded.read()
                f.write(content)
            saved_url_or_path = self.storage_repo.save_bytes("", uploaded.filename, content)

            mime_type, _ = mimetypes.guess_type(local_tmp_path)
            if not mime_type:
                mime_type = "image/jpeg"

            with open(local_tmp_path, "rb") as img_f:
                image_bytes = img_f.read()

            analysis_text = self.ai_provider.generate_text(prompt, image_bytes, mime_type)

            thumbnail_url_or_path = create_thumbnail(saved_url_or_path, local_source_path=local_tmp_path)

            record = self.analysis_repo.create(
                user_id=user_id,
                image_url=saved_url_or_path,
                ai_report=analysis_text,
                thumbnail_url=thumbnail_url_or_path,
            )
            created.append(record)

        return created

    def history_for_user(self, user_id: str) -> List[AnalysisRecord]:
        if not self.user_repo.get_by_id(user_id):
            raise HTTPException(status_code=404, detail="User not found")
        return self.analysis_repo.list_for_user(user_id)


