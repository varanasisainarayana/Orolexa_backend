from typing import Protocol


class RateLimiter(Protocol):
    def allow(self, key: str, max_requests: int, window_seconds: int) -> bool:
        ...


