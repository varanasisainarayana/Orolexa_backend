from dataclasses import dataclass
from typing import List, Optional
from fastapi import UploadFile
from io import BytesIO

from app.application.services.analysis_service import AnalysisService


@dataclass
class FakeRecord:
    id: int
    user_id: str
    image_url: str
    ai_report: str
    thumbnail_url: Optional[str]
    created_at: __import__('datetime').datetime


class FakeAnalysisRepo:
    def __init__(self):
        self.rows: List[FakeRecord] = []
        self._id = 1

    def create(self, user_id: str, image_url: str, ai_report: str, thumbnail_url: Optional[str]):
        rec = FakeRecord(self._id, user_id, image_url, ai_report, thumbnail_url, __import__('datetime').datetime.utcnow())
        self.rows.append(rec)
        self._id += 1
        return rec

    def list_for_user(self, user_id: str) -> List[FakeRecord]:
        return [r for r in self.rows if r.user_id == user_id]


class FakeUserRepo:
    def __init__(self, user_exists: bool = True):
        self.user_exists = user_exists

    def get_by_id(self, user_id: str):
        return object() if self.user_exists else None


class FakeAI:
    def generate_text(self, prompt: str, image_bytes: bytes, mime_type: str) -> str:
        return "ok"


class FakeStorage:
    def save_bytes(self, subdir: str, filename: str, data: bytes) -> str:
        return f"/tmp/{filename}"


class DummyUpload:
    def __init__(self, filename: str, content_type: str = "image/jpeg"):
        self.filename = filename
        self.content_type = content_type
        self.file = BytesIO(b"imagebytes")

    async def read(self):
        return b"imagebytes"


import pytest


@pytest.mark.asyncio
async def test_analyze_images_happy_path(tmp_path, monkeypatch):
    repo = FakeAnalysisRepo()
    users = FakeUserRepo(user_exists=True)
    ai = FakeAI()
    storage = FakeStorage()
    svc = AnalysisService(analysis_repo=repo, user_repo=users, ai_provider=ai, storage_repo=storage)

    files = [DummyUpload("a.jpg"), DummyUpload("b.jpg")]
    out = await svc.analyze_images("u1", files, prompt="p")

    assert len(out) == 2
    assert repo.rows[0].ai_report == "ok"


