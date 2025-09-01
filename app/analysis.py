# app/analysis.py
from typing import List, Union
from fastapi import APIRouter, File, UploadFile, Depends, HTTPException, Request
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


@router.post("/quick-assessment")
async def quick_assessment(
    file1: UploadFile = File(...),  # Required
    file2: UploadFile = File(None), # Optional
    file3: UploadFile = File(None), # Optional
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Quick assessment endpoint that provides structured output including:
    - Rating out of 5
    - Risk level (High/Moderate/Low)
    - Overall health assessment
    - Detected issues (top 3)
    - Recommended precautions
    """
    files = [f for f in [file1, file2, file3] if f is not None]
    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    # Resolve user
    user = session.exec(select(User).where(User.id == current_user)).first()
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

        # Quick Assessment Prompt
        prompt = """
You are a professional dental AI assistant. Analyze the provided dental image and provide a structured quick assessment.

**IMPORTANT: Respond in the exact JSON format specified below. Do not include any other text.**

Analyze the dental image and provide your assessment in this exact JSON format:

{
    "rating": <number from 1-5>,
    "risk_level": "<High/Moderate/Low>",
    "overall_health": "<brief description like 'Fair health', 'Good health', 'Poor health'>",
    "detected_issues": [
        "<issue 1>",
        "<issue 2>", 
        "<issue 3>"
    ],
    "recommended_precautions": [
        "<precaution 1>",
        "<precaution 2>",
        "<precaution 3>"
    ]
}

**Assessment Guidelines:**
- Rating: 1=Poor, 2=Fair, 3=Average, 4=Good, 5=Excellent
- Risk Level: Based on severity of detected issues
- Overall Health: Brief assessment of general dental health
- Detected Issues: Top 3 most important issues found
- Recommended Precautions: Top 3 actionable recommendations

**Response Requirements:**
- Return ONLY valid JSON
- No additional text or explanations
- If image quality is poor, still provide assessment based on what's visible
- If no teeth are visible, indicate this in the issues
- Be professional and accurate in your assessment
"""

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
            "message": "Quick assessment completed",
            "results": results
        }
    }


@router.post("/detailed-analysis")
async def detailed_analysis(
    file1: UploadFile = File(...),  # Required
    file2: UploadFile = File(None), # Optional
    file3: UploadFile = File(None), # Optional
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Detailed analysis endpoint that provides in-depth analysis of 4 major problems
    """
    files = [f for f in [file1, file2, file3] if f is not None]
    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    # Resolve user
    user = session.exec(select(User).where(User.id == current_user)).first()
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

        # Detailed Analysis Prompt
        prompt = """
You are a professional dental AI assistant. Analyze the provided dental image and provide a detailed analysis of the 4 major problems found.

**IMPORTANT: Provide a comprehensive analysis focusing on the 4 most significant dental issues.**

**Analysis Structure:**
Please provide your detailed analysis in the following format:

**MAJOR PROBLEM 1: [Problem Name]**
- **Description:** [Detailed description of the problem]
- **Location:** [Specific tooth/area affected]
- **Severity:** [Mild/Moderate/Severe]
- **Causes:** [What likely caused this problem]
- **Symptoms:** [What symptoms this might cause]
- **Treatment Options:** [Professional treatment recommendations]
- **Prevention:** [How to prevent this in the future]

**MAJOR PROBLEM 2: [Problem Name]**
- **Description:** [Detailed description of the problem]
- **Location:** [Specific tooth/area affected]
- **Severity:** [Mild/Moderate/Severe]
- **Causes:** [What likely caused this problem]
- **Symptoms:** [What symptoms this might cause]
- **Treatment Options:** [Professional treatment recommendations]
- **Prevention:** [How to prevent this in the future]

**MAJOR PROBLEM 3: [Problem Name]**
- **Description:** [Detailed description of the problem]
- **Location:** [Specific tooth/area affected]
- **Severity:** [Mild/Moderate/Severe]
- **Causes:** [What likely caused this problem]
- **Symptoms:** [What symptoms this might cause]
- **Treatment Options:** [Professional treatment recommendations]
- **Prevention:** [How to prevent this in the future]

**MAJOR PROBLEM 4: [Problem Name]**
- **Description:** [Detailed description of the problem]
- **Location:** [Specific tooth/area affected]
- **Severity:** [Mild/Moderate/Severe]
- **Causes:** [What likely caused this problem]
- **Symptoms:** [What symptoms this might cause]
- **Treatment Options:** [Professional treatment recommendations]
- **Prevention:** [How to prevent this in the future]

**Analysis Guidelines:**
- Focus on the 4 most significant dental health issues
- Be specific about tooth locations and conditions
- Provide detailed explanations for each problem
- Include professional medical terminology
- Give actionable treatment and prevention advice
- If fewer than 4 problems are detected, clearly state this
- If image quality is poor, mention limitations but analyze what's visible
- Be thorough but keep each problem description focused and clear

**Response Requirements:**
- Provide detailed analysis for each of the 4 major problems
- Use professional dental terminology
- Include specific treatment recommendations
- Focus on actionable advice
- Keep the tone professional and educational
- If no significant problems are found, provide general dental health assessment
"""

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
            "message": "Detailed analysis completed",
            "results": results
        }
    }


@router.post("/analyze-images")
async def analyze_images(
    file1: UploadFile = File(...),  # Required
    file2: UploadFile = File(None), # Optional
    file3: UploadFile = File(None), # Optional
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    files = [f for f in [file1, file2, file3] if f is not None]
    if not files:
        raise HTTPException(status_code=400, detail="At least one file must be uploaded.")

    # Resolve user
    user = session.exec(select(User).where(User.id == current_user)).first()
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
    current_user: str = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    try:
        logger.info(f"Getting history for user: {current_user}")
        user = session.exec(select(User).where(User.id == current_user)).first()
        if not user:
            logger.error(f"User not found for ID: {current_user}")
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
