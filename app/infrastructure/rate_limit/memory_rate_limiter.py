import time
from typing import Dict, Any

from ...application.ports.rate_limiter import RateLimiter


class InMemoryRateLimiter(RateLimiter):
    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def allow(self, key: str, max_requests: int, window_seconds: int) -> bool:
        now = time.time()
        window_start = now - window_seconds
        rec = self._store.get(key)
        if not rec:
            self._store[key] = {"times": [now]}
            return True
        # prune
        rec["times"] = [t for t in rec["times"] if t > window_start]
        if len(rec["times"]) >= max_requests:
            return False
        rec["times"].append(now)
        return True


