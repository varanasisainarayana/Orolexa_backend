import time
from typing import Optional

try:
    import redis
except Exception:  # pragma: no cover
    redis = None

from ...application.ports.rate_limiter import RateLimiter


class RedisRateLimiter(RateLimiter):
    def __init__(self, url: str, prefix: str = "rl:") -> None:
        if redis is None:
            raise RuntimeError("redis package is not installed")
        self.client = redis.Redis.from_url(url)
        self.prefix = prefix

    def allow(self, key: str, max_requests: int, window_seconds: int) -> bool:
        rk = f"{self.prefix}{key}:{window_seconds}"
        # Use Redis INCR with EXPIRE for fixed window
        pipe = self.client.pipeline()
        pipe.incr(rk, 1)
        pipe.expire(rk, window_seconds)
        count, _ = pipe.execute()
        return int(count) <= int(max_requests)


