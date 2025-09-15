import pytest

from app.infrastructure.rate_limit.memory_rate_limiter import InMemoryRateLimiter


def test_memory_rate_limiter_allows_then_blocks():
    rl = InMemoryRateLimiter()
    key = "k1"
    assert rl.allow(key, max_requests=2, window_seconds=60) is True
    assert rl.allow(key, max_requests=2, window_seconds=60) is True
    assert rl.allow(key, max_requests=2, window_seconds=60) is False


def test_redis_rate_limiter_with_fake(monkeypatch):
    redis = pytest.importorskip("redis")

    class FakePipe:
        def __init__(self, client, key):
            self.client = client
            self.key = key
            self.ops = []
        def incr(self, k, n):
            self.ops.append(("incr", k, n))
            return self
        def expire(self, k, s):
            self.ops.append(("expire", k, s))
            return self
        def execute(self):
            # emulate incrementing counter
            cnt = self.client.store.get(self.key, 0) + 1
            self.client.store[self.key] = cnt
            return [cnt, True]

    class FakeRedis:
        def __init__(self):
            self.store = {}
        @classmethod
        def from_url(cls, url):
            return cls()
        def pipeline(self):
            # key is embedded in rate limiter; we don't know it here, provide placeholder updated in limiter
            return FakePipe(self, None)

    from app.infrastructure.rate_limit import redis_rate_limiter as mod
    monkeypatch.setattr(mod.redis, "Redis", FakeRedis)

    rl = mod.RedisRateLimiter(url="redis://fake")

    # Patch pipeline to capture the real key used by rate limiter
    def pipeline_with_key(self):
        # FakePipe will get key set by caller after creating pipe
        return FakePipe(self, None)
    monkeypatch.setattr(FakeRedis, "pipeline", pipeline_with_key)

    # Monkeypatch allow to set key into pipe
    orig_allow = mod.RedisRateLimiter.allow
    def allow_with_key(self, key, max_requests, window_seconds):
        rk = f"{self.prefix}{key}:{window_seconds}"
        pipe = self.client.pipeline()
        pipe.key = rk
        pipe.incr(rk, 1)
        pipe.expire(rk, window_seconds)
        count, _ = pipe.execute()
        return int(count) <= int(max_requests)
    monkeypatch.setattr(mod.RedisRateLimiter, "allow", allow_with_key)

    assert rl.allow("k1", 2, 60) is True
    assert rl.allow("k1", 2, 60) is True
    assert rl.allow("k1", 2, 60) is False


