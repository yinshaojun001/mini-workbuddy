from collections import defaultdict, deque
from threading import RLock
from time import monotonic

from app.errors import AppError


class RateLimiter:
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = RLock()

    def check(self, key: str, limit: int, window_seconds: int = 60) -> None:
        now = monotonic()
        with self._lock:
            events = self._events[key]
            while events and events[0] <= now - window_seconds:
                events.popleft()
            if len(events) >= limit:
                retry_after = max(1, round(window_seconds - (now - events[0])))
                raise AppError("RATE_LIMITED", "请求过于频繁，请稍后再试", 429, {"retry_after": retry_after})
            events.append(now)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


public_rate_limiter = RateLimiter()
