from twilio.rest import Client
from typing import Optional
from ...config import settings
from ...application.ports.otp_provider import OTPProvider

class TwilioOTPProvider(OTPProvider):
    def __init__(self, client: Optional[Client] = None):
        self.client = client or Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        self.verify_sid = settings.TWILIO_VERIFY_SERVICE_SID

    def send(self, phone: str) -> str:
        if not self.verify_sid:
            raise RuntimeError("Twilio Verify Service SID not configured")
        verification = self.client.verify.services(self.verify_sid).verifications.create(to=phone, channel="sms")
        return verification.sid

    def verify(self, phone: str, code: str) -> bool:
        if not self.verify_sid:
            raise RuntimeError("Twilio Verify Service SID not configured")
        check = self.client.verify.services(self.verify_sid).verification_checks.create(to=phone, code=code)
        return check.status == "approved"
