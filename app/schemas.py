from pydantic import BaseModel


# =========================
# OTP Send Requests
# =========================
class SendOTPRequest(BaseModel):
    mobile_number: str


# =========================
# OTP Verify Requests (Login)
# =========================
class VerifyOTPRequest(BaseModel):
    mobile_number: str
    otp_code: str


# =========================
# OTP Verify Requests (Registration)
# =========================
class RegisterVerifyRequest(BaseModel):
    mobile_number: str
    otp_code: str
    full_name: str  # REQUIRED for registration
    profile_photo_url: str  # REQUIRED for registration


# =========================
# Common Response Schemas
# =========================
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class MessageResponse(BaseModel):
    message: str
