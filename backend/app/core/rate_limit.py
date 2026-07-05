from __future__ import annotations

from collections import defaultdict, deque
from time import monotonic

from fastapi import HTTPException, status


class InMemoryRateLimiter:
    def __init__(self, *, limit: int = 120, window_seconds: int = 60) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = monotonic()
        queue = self.events[key]
        while queue and now - queue[0] > self.window_seconds:
            queue.popleft()
        if len(queue) >= self.limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        queue.append(now)


rate_limiter = InMemoryRateLimiter()

