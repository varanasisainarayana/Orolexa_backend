from typing import Optional, Dict, Any, Protocol


class AuditLogger(Protocol):
    def log(self, action: str, phone: str, user_id: Optional[str] = None, request_id: Optional[str] = None, ip_address: Optional[str] = None, success: bool = True, details: Optional[Dict[str, Any]] = None) -> None:
        ...


