# app/analysis.py
from typing import List, Union
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException
from sqlmodel import Session, select
import mimetypes
import os
import google.generativeai as genai
from datetime import datetime
import traceback
from PIL import Image
import io
import logging

from .utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .database import get_session
from .models import AnalysisHistory, User
from .config import settings
from .storage import get_storage

# Configure logging
logger = logging.getLogger(__name__)

# Configure Gemini API from env (make sure GEMINI_API_KEY is set)
genai.configure(api_key=settings.GEMINI_API_KEY)

router = APIRouter(prefix="/analysis", tags=["Analysis"])

# Auth scheme
oauth2_scheme = HTTPBearer(auto_error=False)

# Dependency to get current user from JWT
def get_current_user(request, credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
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
    
    # Handle both string and int user IDs
    try:
        user_id_int = int(user_id)
        logger.info(f"Successfully authenticated user ID: {user_id_int}")
        return user_id_int
    except (ValueError, TypeError):
        logger.warning(f"Invalid user ID format in token: {user_id}")
        raise HTTPException(status_code=401, detail="Invalid token: invalid user ID format")

def _extract_text_from_gemini_result(result) -> str:
    """Safely extract text from different Gemini result shapes."""
    if getattr(result, "text", None):
        return result.text
    try:
        if getattr(result, "candidates", None):
            cand = result.candidates[0]
            if getattr(cand, "content", None):
                parts = getattr(cand.content, "parts", None)
                if parts:
                    if isinstance(parts[0], str):
                        return parts[0]
                    return getattr(parts[0], "text", str(parts[0]))
            return getattr(cand, "text", str(cand))
    except Exception:
        pass
    return str(result)

def create_thumbnail(image_path_or_url: str, local_source_path: str = None, thumbnail_size: tuple = None) -> str:
    """Create a thumbnail from a local image file and store via StorageService.
    If using S3, caller should pass a local_source_path for reading bytes.
    Returns a URL or local path depending on storage backend.
    """
    if thumbnail_size is None:
        thumbnail_size = settings.THUMBNAIL_SIZE
    try:
        storage = get_storage()
        # We must read from local file, so ensure path is available
        src_path = local_source_path or image_path_or_url
        with Image.open(src_path) as img:
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            buf = io.BytesIO()
            img.save(buf, format='JPEG', quality=85, optimize=True)
            buf.seek(0)
            return storage.save_bytes("thumbnails", os.path.basename(src_path), buf.read())
    except Exception as e:
        print(f"Error creating thumbnail: {e}")
        return None


@router.post("/analyze-images")
async def analyze_images(
    file1: UploadFile = File(...),  # Required
    file2: UploadFile = File(None), # Optional
    file3: UploadFile = File(None), # Optional
    current_user: Union[int, str] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    files = [f for f in [file1, file2, file3] if f is not None]
    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    # Resolve user
    try:
        user = session.exec(select(User).where(User.id == int(current_user))).first()
    except ValueError:
        user = session.exec(select(User).where(User.mobile_number == current_user)).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    storage = get_storage()
    results = []

    for uploaded in files:
        # Validate file type
        if uploaded.content_type not in settings.ALLOWED_IMAGE_TYPES:
            raise HTTPException(status_code=415, detail=f"File type {uploaded.content_type} not allowed")
        # Validate file size
        uploaded.file.seek(0, 2)
        file_size = uploaded.file.tell()
        uploaded.file.seek(0)
        if file_size > settings.MAX_FILE_SIZE:
            raise HTTPException(status_code=413, detail=f"File too large (max {settings.MAX_FILE_SIZE // (1024*1024)}MB)")

        # Save file using storage service (also keep local temp path for thumbnail)
        tmp_dir = settings.UPLOAD_DIR
        os.makedirs(tmp_dir, exist_ok=True)
        local_tmp_path = os.path.join(tmp_dir, f"{int(datetime.utcnow().timestamp()*1000)}_{uploaded.filename}")
        with open(local_tmp_path, "wb") as f:
            content = await uploaded.read()
            f.write(content)
        saved_url_or_path = storage.save_bytes("", uploaded.filename, content)

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(local_tmp_path)
        if not mime_type:
            mime_type = "image/jpeg"

        # Read bytes
        with open(local_tmp_path, "rb") as img_f:
            image_bytes = img_f.read()

        # Gemini AI
        prompt = (
            """
You are a professional dental AI assistant. Analyze the provided dental image and provide a comprehensive assessment.

**Instructions:**
1. Examine the image carefully for dental health indicators
2. Provide a detailed analysis in a professional, medical tone
3. Focus on both positive aspects and areas of concern
4. Be specific about tooth locations and conditions
5. Provide actionable recommendations when appropriate

**Analysis Structure:**
Please provide your analysis in the following format:

**Overall Assessment:**
[Brief summary of dental health status]
Also give overall rating of the dental health of the patient out of 5.

**Detailed Findings:**
- [Specific observations about teeth, gums, and oral health]
- [Note any visible issues like cavities, discoloration, gaps, etc.]
- [Comment on gum health and overall oral hygiene]

**Areas of Concern:**
- [List any detected issues or potential problems]
- [Specify severity and urgency if applicable]

**Positive Aspects:**
- [Highlight good dental health indicators]
- [Note healthy teeth, gums, or good oral hygiene signs]

**Recommendations:**
- [Suggest specific actions or lifestyle changes]
- [Mention if professional dental consultation is recommended]
- [Provide preventive care advice]

**Important Notes:**
- If the image quality is poor or unclear, mention this limitation
- If the image doesn't show teeth clearly, state this clearly
- Be encouraging but honest about any concerns
- Use professional medical terminology appropriately
- Keep the tone helpful and educational

**Response Guidelines:**
- Keep the total response between 200-400 words
- Use clear, easy-to-understand language
- Be specific about tooth locations (e.g., "upper right molar", "lower left incisor")
- If no teeth are visible, clearly state this
- Focus on what can be observed from the image

Please analyze the dental image and provide your assessment following these guidelines.
"""
        )
        model = genai.GenerativeModel(settings.GEMINI_MODEL)
        result = model.generate_content([
            prompt,
            {"mime_type": mime_type, "data": image_bytes}
        ])
        analysis_text = result.text if hasattr(result, "text") else str(result)

        # Create thumbnail and save via storage
        thumbnail_url_or_path = create_thumbnail(saved_url_or_path, local_source_path=local_tmp_path)

        # Save to DB
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

        # Get base URL for image serving
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

    return {
        "success": True,
        "data": {
            "message": "Analysis completed",
            "results": results
        }
    }


@router.get("/history")
def get_history(
    current_user: Union[int, str] = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        logger.info(f"Getting history for user: {current_user} (type: {type(current_user)})")
        user = None
        try:
            user_id_candidate = int(current_user)
            user = session.exec(select(User).where(User.id == user_id_candidate)).first()
            logger.info(f"Found user by ID: {user_id_candidate}")
        except Exception as e:
            logger.warning(f"Failed to find user by ID {current_user}: {e}")
            user = session.exec(select(User).where(User.mobile_number == current_user)).first()
            logger.info(f"Found user by mobile number: {current_user}")
        if not user:
            logger.error(f"User not found for ID/mobile: {current_user}")
            raise HTTPException(status_code=404, detail="User not found")
        histories = session.exec(
            select(AnalysisHistory)
            .where(AnalysisHistory.user_id == user.id)
            .order_by(AnalysisHistory.created_at.desc())
        ).all()
        
        logger.info(f"Found {len(histories)} history entries for user {user.id}")
        
        BASE_URL = settings.BASE_URL
        history_data = [
            {
                "id": h.id,
                "analysis": h.ai_report,
                "image_url": h.image_url if h.image_url.startswith("http") else f"{BASE_URL}/{h.image_url}",
                "thumbnail_url": h.thumbnail_url if (h.thumbnail_url and h.thumbnail_url.startswith("http")) else (f"{BASE_URL}/{h.thumbnail_url}" if h.thumbnail_url else None),
                "doctor_name": h.doctor_name,
                "status": h.status,
                "timestamp": h.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            for h in histories
        ]
        
        logger.info(f"Successfully retrieved history for user {user.id}")
        return {"success": True, "data": history_data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in get_history: {str(e)}", exc_info=True)
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
