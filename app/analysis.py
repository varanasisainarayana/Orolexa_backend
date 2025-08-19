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

from .utils import decode_jwt_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from .database import get_session
from .models import AnalysisHistory, User
from .config import settings

# Configure Gemini API from env (make sure GEMINI_API_KEY is set)
genai.configure(api_key=settings.GEMINI_API_KEY)

router = APIRouter(prefix="/analysis", tags=["Analysis"])

# Auth scheme
oauth2_scheme = HTTPBearer()

# Dependency to get current user from JWT
def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(oauth2_scheme)):
    token = credentials.credentials
    payload = decode_jwt_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return int(payload.get("sub"))  # user_id as int

def _extract_text_from_gemini_result(result) -> str:
    """Safely extract text from different Gemini result shapes."""
    # Preferred property
    if getattr(result, "text", None):
        return result.text
    # fallback to candidates
    try:
        if getattr(result, "candidates", None):
            cand = result.candidates[0]
            # some SDKs put text under 'content' -> 'parts'
            if getattr(cand, "content", None):
                parts = getattr(cand.content, "parts", None)
                if parts:
                    # parts may be list of strings or objects
                    if isinstance(parts[0], str):
                        return parts[0]
                    # try nested attribute
                    return getattr(parts[0], "text", str(parts[0]))
            return getattr(cand, "text", str(cand))
    except Exception:
        pass
    # last resort
    return str(result)

def create_thumbnail(image_path: str, thumbnail_size: tuple = None) -> str:
    """Create a thumbnail from the original image."""
    if thumbnail_size is None:
        thumbnail_size = settings.THUMBNAIL_SIZE
        
    try:
        # Create thumbnails directory
        thumbnails_dir = f"{settings.UPLOAD_DIR}/thumbnails"
        os.makedirs(thumbnails_dir, exist_ok=True)
        
        # Open and resize image
        with Image.open(image_path) as img:
            # Convert to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Create thumbnail
            img.thumbnail(thumbnail_size, Image.Resampling.LANCZOS)
            
            # Generate thumbnail filename
            filename = os.path.basename(image_path)
            name, ext = os.path.splitext(filename)
            thumbnail_filename = f"thumb_{name}{ext}"
            thumbnail_path = os.path.join(thumbnails_dir, thumbnail_filename)
            
            # Save thumbnail
            img.save(thumbnail_path, quality=85, optimize=True)
            
            return thumbnail_path
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
    """
    Accept exactly 3 file inputs from the frontend, with file1 required.
    file2 and file3 are optional.
    """
    # Collect only provided files
    files = [f for f in [file1, file2, file3] if f is not None]

    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    uploads_dir = settings.UPLOAD_DIR
    os.makedirs(uploads_dir, exist_ok=True)

    # Resolve user
    try:
        user = session.exec(select(User).where(User.id == int(current_user))).first()
    except ValueError:
        user = session.exec(select(User).where(User.mobile_number == current_user)).first()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

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
        
        # Save file
        timestamped_name = f"{int(datetime.utcnow().timestamp()*1000)}_{uploaded.filename}"
        image_path = os.path.join(uploads_dir, timestamped_name)

        with open(image_path, "wb") as f:
            content = await uploaded.read()
            f.write(content)

        # Detect MIME type
        mime_type, _ = mimetypes.guess_type(image_path)
        if not mime_type:
            mime_type = "image/jpeg"

        # Read bytes
        with open(image_path, "rb") as img_f:
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
        result = model.generate_content(
            [
                prompt,
                {"mime_type": mime_type, "data": image_bytes}
            ]
        )
        analysis_text = result.text if hasattr(result, "text") else str(result)

        # Create thumbnail
        thumbnail_path = create_thumbnail(image_path)
        
        # Save to DB with new fields
        history_entry = AnalysisHistory(
            user_id=user.id,
            image_url=image_path,
            ai_report=analysis_text,
            doctor_name="Dr. AI Assistant",
            status="completed",
            thumbnail_url=thumbnail_path
        )
        session.add(history_entry)
        session.commit()
        session.refresh(history_entry)

        # Get base URL for image serving
        BASE_URL = settings.BASE_URL
        
        results.append({
            "filename": uploaded.filename,
            "saved_path": image_path,
            "image_url": f"{BASE_URL}/{image_path}",
            "thumbnail_url": f"{BASE_URL}/{thumbnail_path}" if thumbnail_path else None,
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
    """
    Return list of past analyses for the current user (newest first).
    """
    try:
        # Resolve user like above
        user = None
        try:
            user_id_candidate = int(current_user)
            user = session.exec(select(User).where(User.id == user_id_candidate)).first()
        except Exception:
            user = session.exec(select(User).where(User.mobile_number == current_user)).first()

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        histories = session.exec(
            select(AnalysisHistory)
            .where(AnalysisHistory.user_id == user.id)
            .order_by(AnalysisHistory.created_at.desc())
        ).all()

        # Get base URL for image serving
        BASE_URL = settings.BASE_URL
        
        history_data = [
            {
                "id": h.id,
                "analysis": h.ai_report,
                "image_url": f"{BASE_URL}/{h.image_url}",
                "thumbnail_url": f"{BASE_URL}/{h.thumbnail_url}" if h.thumbnail_url else None,
                "doctor_name": h.doctor_name,
                "status": h.status,
                "timestamp": h.created_at.strftime("%Y-%m-%d %H:%M:%S")
            }
            for h in histories
        ]

        return {
            "success": True,
            "data": history_data
        }

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))
