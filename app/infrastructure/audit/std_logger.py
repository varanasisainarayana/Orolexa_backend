import json
import logging
from typing import Optional, Dict, Any

from ...application.ports.audit_logger import AuditLogger


class StdAuditLogger(AuditLogger):
    def __init__(self) -> None:
        self._logger = logging.getLogger(__name__)

    def log(self, action: str, phone: str, user_id: Optional[str] = None, request_id: Optional[str] = None, ip_address: Optional[str] = None, success: bool = True, details: Optional[Dict[str, Any]] = None) -> None:
        entry = {
            "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
            "action": action,
            "phone_hash": __import__("hashlib").sha256(phone.encode()).hexdigest(),
            "user_id": user_id,
            "request_id": request_id,
            "ip_address": ip_address,
            "success": success,
            "details": details or {},
        }
        self._logger.info(f"AUDIT: {json.dumps(entry)}")


