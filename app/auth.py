# app/auth.py
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from sqlmodel import Session, select
from .database import engine
from .models import OTPRequest, User
from .schemas import SendOTPRequest, VerifyOTPRequest
from .utils import create_jwt_token
from twilio.rest import Client
import os
import uuid
import shutil
from datetime import datetime
import traceback
from .config import settings

router = APIRouter(prefix="/auth", tags=["Authentication"])

# Twilio config (from settings)
client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)


# -----------------------
# LOGIN FLOW (only for registered users)
# -----------------------
@router.post("/login/send-otp")
def login_send_otp(payload: SendOTPRequest):
    try:
        with Session(engine) as session:
            user = session.exec(select(User).where(User.mobile_number == payload.mobile_number)).first()
            if not user:
                raise HTTPException(status_code=404, detail="Mobile number not registered. Please register first.")

        verification = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID) \
            .verifications.create(to=payload.mobile_number, channel="sms")

        # Store OTP request history (masked OTP)
        with Session(engine) as session:
            session.add(OTPRequest(mobile_number=payload.mobile_number, otp_code="***"))
            session.commit()

        return {"message": "OTP sent successfully for login", "status": verification.status}

    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Login send OTP error: {e}")


@router.post("/login/verify-otp")
def login_verify_otp(payload: VerifyOTPRequest):
    try:
        verification_check = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID) \
            .verification_checks.create(to=payload.mobile_number, code=payload.otp_code)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Twilio error: {e}")

    if verification_check.status != "approved":
        raise HTTPException(status_code=400, detail="Invalid OTP")

    with Session(engine) as session:
        # Ensure user exists
        user = session.exec(select(User).where(User.mobile_number == payload.mobile_number)).first()
        if not user:
            raise HTTPException(status_code=404, detail="Mobile number not registered. Please register first.")

        # Mark latest OTP as verified
        otp_entry = session.exec(
            select(OTPRequest)
            .where(OTPRequest.mobile_number == payload.mobile_number)
            .order_by(OTPRequest.created_at.desc())
        ).first()
        if otp_entry:
            otp_entry.is_verified = True
            session.add(otp_entry)
            session.commit()

        session.refresh(user)
        token = create_jwt_token({"sub": str(user.id)})

        return {"access_token": token, "token_type": "bearer"}


# -----------------------
# REGISTER FLOW
# -----------------------
@router.post("/register/send-otp")
def register_send_otp(
    mobile_number: str = Form(...),
    full_name: str = Form(...),
    profile_photo: UploadFile = File(...)
):
    # Validate file type
    if profile_photo.content_type not in settings.ALLOWED_IMAGE_TYPES:
        raise HTTPException(status_code=415, detail="Invalid file type")
        
    # Validate file size
    profile_photo.file.seek(0, 2)
    file_size = profile_photo.file.tell()
    profile_photo.file.seek(0)
    
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large")
    
    uploads_dir = f"{settings.UPLOAD_DIR}/profiles"
    os.makedirs(uploads_dir, exist_ok=True)
    ext = os.path.splitext(profile_photo.filename)[1]
    filename = f"{uuid.uuid4().hex}{ext}"
    saved_path = os.path.join(uploads_dir, filename)

    try:
        with open(saved_path, "wb") as f:
            shutil.copyfileobj(profile_photo.file, f)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Could not save profile photo: {e}")

    try:
        verification = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID) \
            .verifications.create(to=mobile_number, channel="sms")
    except Exception as e:
        traceback.print_exc()
        try:
            os.remove(saved_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Twilio error: {e}")

    with Session(engine) as session:
        otp_entry = OTPRequest(
            mobile_number=mobile_number,
            otp_code="***",
            full_name=full_name,
            profile_photo_url=saved_path,
            is_verified=False
        )
        session.add(otp_entry)
        session.commit()

    return {"message": "OTP sent successfully for registration", "status": verification.status}


@router.post("/register/verify-otp")
def register_verify_otp(payload: VerifyOTPRequest):
    try:
        verification_check = client.verify.services(settings.TWILIO_VERIFY_SERVICE_SID) \
            .verification_checks.create(to=payload.mobile_number, code=payload.otp_code)
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Twilio error: {e}")

    if verification_check.status != "approved":
        raise HTTPException(status_code=400, detail="Invalid OTP")

    with Session(engine) as session:
        otp_entry = session.exec(
            select(OTPRequest)
            .where(OTPRequest.mobile_number == payload.mobile_number)
            .order_by(OTPRequest.created_at.desc())
        ).first()

        if not otp_entry or not otp_entry.full_name or not otp_entry.profile_photo_url:
            raise HTTPException(status_code=400, detail="No registration data found. Please call register/send-otp first.")

        otp_entry.is_verified = True
        session.add(otp_entry)
        session.commit()

        # Create or update user
        user = session.exec(select(User).where(User.mobile_number == payload.mobile_number)).first()
        if not user:
            user = User(
                mobile_number=payload.mobile_number,
                full_name=otp_entry.full_name,
                profile_photo_url=otp_entry.profile_photo_url
            )
            session.add(user)
        else:
            user.full_name = otp_entry.full_name
            user.profile_photo_url = otp_entry.profile_photo_url
            session.add(user)

        session.commit()
        session.refresh(user)

        token = create_jwt_token({"sub": str(user.id)})
        return {"access_token": token, "token_type": "bearer"}
