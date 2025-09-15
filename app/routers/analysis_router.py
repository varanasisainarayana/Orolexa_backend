from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel import Session, select
from sqlmodel import Session as _Session
import mimetypes
import os
import google.generativeai as genai
from datetime import datetime
import traceback
import logging

from ..utils import decode_jwt_token
from ..persistence.database import get_session
from ..models import AnalysisHistory, User
from ..config import settings
from ..shared.storage import get_storage
from ..media_utils import create_thumbnail
from ..application.services.analysis_service import AnalysisService
from ..application.ports.ai_provider import AIProvider
from ..infrastructure.ai.gemini_provider import GeminiProvider
from ..infrastructure.storage.local_storage import LocalStorageRepository
from ..infrastructure.persistence.sqlalchemy.repositories.analysis_repository_sql import SqlAnalysisRepository
from ..infrastructure.persistence.sqlalchemy.repositories.user_repository_sql import SqlUserRepository
from ..persistence.database import engine as _engine

logger = logging.getLogger(__name__)

genai.configure(api_key=settings.GEMINI_API_KEY)

router = APIRouter(prefix="/analysis", tags=["Analysis"])

oauth2_scheme = HTTPBearer(auto_error=False)

def get_current_user(request: Request, credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = None
    if credentials and credentials.credentials:
        token = credentials.credentials
    else:
        token = request.cookies.get("access_token")
    payload = decode_jwt_token(token)
    if not payload:
        logger.warning("JWT token decode failed - invalid or expired token")
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        logger.warning("JWT token missing user ID")
        raise HTTPException(status_code=401, detail="Invalid token: missing user ID")
    logger.info(f"Successfully authenticated user ID: {user_id}")
    return user_id


def get_analysis_service() -> AnalysisService:
    session = _Session(_engine)
    analysis_repo = SqlAnalysisRepository(session)
    user_repo = SqlUserRepository(session)
    ai_provider: AIProvider = GeminiProvider()
    storage_repo = LocalStorageRepository()
    return AnalysisService(analysis_repo=analysis_repo, user_repo=user_repo, ai_provider=ai_provider, storage_repo=storage_repo)


@router.post("/quick-assessment")
async def quick_assessment(
    file1: UploadFile = File(...),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None),
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session),
    analysis_service: AnalysisService = Depends(get_analysis_service),
):
    files = [f for f in [file1, file2, file3] if f is not None]
    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    user = session.exec(select(User).where(User.id == current_user)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    prompt = """
You are a professional dental AI assistant. Analyze the provided dental image and provide a structured quick assessment.

**IMPORTANT: Respond in the exact JSON format specified below. Do not include any other text.**
"""
    created = await analysis_service.analyze_images(current_user, files, prompt)
    BASE_URL = settings.BASE_URL
    results = [
        {
            "filename": f.filename,
            "saved_path": r.image_url,
            "image_url": r.image_url if r.image_url.startswith("http") else f"{BASE_URL}/{r.image_url}",
            "thumbnail_url": r.thumbnail_url if (r.thumbnail_url and r.thumbnail_url.startswith("http")) else (f"{BASE_URL}/{r.thumbnail_url}" if r.thumbnail_url else None),
            "analysis": r.ai_report,
            "history_id": r.id,
            "doctor_name": "Dr. AI Assistant",
            "status": "completed",
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for f, r in zip([f for f in [file1, file2, file3] if f is not None], created)
    ]
    return {"success": True, "data": {"message": "Quick assessment completed", "results": results}}


@router.post("/detailed-analysis")
async def detailed_analysis(
    file1: UploadFile = File(...),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None),
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    files = [f for f in [file1, file2, file3] if f is not None]
    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    user = session.exec(select(User).where(User.id == current_user)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    analysis_service: AnalysisService = get_analysis_service()
    results = []

    for uploaded in files:
        if uploaded.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail=f"File type {uploaded.content_type} not allowed")
        uploaded.file.seek(0, 2)
        file_size = uploaded.file.tell()
        uploaded.file.seek(0)
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large (max {settings.MAX_FILE_SIZE // (1024*1024)}MB)")

        prompt = "Analyze the provided dental image and provide a detailed analysis."
        created = await analysis_service.analyze_images(current_user, [uploaded], prompt)
        r = created[0]
        BASE_URL = settings.BASE_URL
        results.append({
            "filename": uploaded.filename,
            "saved_path": r.image_url,
            "image_url": r.image_url if r.image_url.startswith("http") else f"{BASE_URL}/{r.image_url}",
            "thumbnail_url": r.thumbnail_url if (r.thumbnail_url and r.thumbnail_url.startswith("http")) else (f"{BASE_URL}/{r.thumbnail_url}" if r.thumbnail_url else None),
            "analysis": r.ai_report,
            "history_id": r.id,
            "doctor_name": "Dr. AI Assistant",
            "status": "completed",
            "created_at": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        })

    return {"success": True, "data": {"message": "Detailed analysis completed", "results": results}}


@router.post("/analyze-images")
async def analyze_images(
    file1: UploadFile = File(...),
    file2: UploadFile = File(None),
    file3: UploadFile = File(None),
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session),
):
    files = [f for f in [file1, file2, file3] if f is not None]
    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    user = session.exec(select(User).where(User.id == current_user)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    storage = get_storage()
    results = []

    for uploaded in files:
        if uploaded.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail=f"File type {uploaded.content_type} not allowed")
        uploaded.file.seek(0, 2)
        file_size = uploaded.file.tell()
        uploaded.file.seek(0)
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large (max {settings.MAX_FILE_SIZE // (1024*1024)}MB)")

        tmp_dir = settings.UPLOAD_DIR
        os.makedirs(tmp_dir, exist_ok=True)
        local_tmp_path = os.path.join(tmp_dir, f"{int(datetime.utcnow().timestamp()*1000)}_{uploaded.filename}")
        with open(local_tmp_path, "wb") as f:
            content = await uploaded.read()
            f.write(content)
        saved_url_or_path = storage.save_bytes("", uploaded.filename, content)

        mime_type, _ = mimetypes.guess_type(local_tmp_path)
        if not mime_type:
            mime_type = "image/jpeg"
        with open(local_tmp_path, "rb") as img_f:
            image_bytes = img_f.read()

        prompt = ("Analyze the dental image and provide your assessment.")
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        result = model.generate_content([
            prompt,
            {"mime_type": mime_type, "data": image_bytes}
        ])
        analysis_text = result.text if hasattr(result, "text") else str(result)

        thumbnail_url_or_path = create_thumbnail(saved_url_or_path, local_source_path=local_tmp_path)

        history_entry = AnalysisHistory(
            user_id=user.id,
            image_url=saved_url_or_path,
            ai_report=analysis_text,
            doctor_name="Dr. AI Assistant",
            status="completed",
            thumbnail_url=thumbnail_url_or_path
        )
        session.add(history_entry)
        session.commit()
        session.refresh(history_entry)

        BASE_URL = settings.BASE_URL
        results.append({
            "filename": uploaded.filename,
            "saved_path": saved_url_or_path,
            "image_url": saved_url_or_path if saved_url_or_path.startswith("http") else f"{BASE_URL}/{saved_url_or_path}",
            "thumbnail_url": thumbnail_url_or_path if (thumbnail_url_or_path and thumbnail_url_or_path.startswith("http")) else (f"{BASE_URL}/{thumbnail_url_or_path}" if thumbnail_url_or_path else None),
            "analysis": analysis_text,
            "history_id": history_entry.id,
            "doctor_name": "Dr. AI Assistant",
            "status": "completed",
            "created_at": history_entry.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })

    return {"success": True, "data": {"message": "Analysis completed", "results": results}}


@router.get("/history")
def get_history(
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        analysis_service: AnalysisService = get_analysis_service()
        records = analysis_service.history_for_user(current_user)
        BASE_URL = settings.BASE_URL
        history_data = [
            {
                "id": r.id,
                "analysis": r.ai_report,
                "image_url": r.image_url if r.image_url.startswith("http") else f"{BASE_URL}/{r.image_url}",
                "thumbnail_url": r.thumbnail_url if (r.thumbnail_url and r.thumbnail_url.startswith("http")) else (f"{BASE_URL}/{r.thumbnail_url}" if r.thumbnail_url else None),
                "doctor_name": "Dr. AI Assistant",
                "status": "completed",
                "timestamp": r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            for r in records
        ]
        return {"success": True, "data": history_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_history: {str(e)}", exc_info=True)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


