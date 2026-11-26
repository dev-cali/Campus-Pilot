
"""Thread-safe request limits for the standalone fictional AI demo."""

import os
import time

from collections import deque
from threading import Lock

from fastapi import HTTPException


class DemoRateLimiter:
    def __init__(self, per_minute: int = 5, per_day: int = 100):
        if per_minute < 1 or per_day < 1:
            raise ValueError("Request limits must be positive.")

        self.per_minute = per_minute
        self.per_day = per_day

        self.minute_requests = deque()
        self.daily_requests = deque()

        self.lock = Lock()

    def check(self) -> None:
        with self.lock:
            now = time.monotonic()

            while (
                self.minute_requests
                and now - self.minute_requests[0] >= 60
            ):
                self.minute_requests.popleft()

            while (
                self.daily_requests
                and now - self.daily_requests[0] >= 86400
            ):
                self.daily_requests.popleft()

            if len(self.daily_requests) >= self.per_day:
                raise HTTPException(
                    status_code=429,
                    detail="Daily AI demo request limit reached.",
                )

            if len(self.minute_requests) >= self.per_minute:
                raise HTTPException(
                    status_code=429,
                    detail="Too many AI requests. Please try again shortly.",
                    headers={"Retry-After": "60"},
                )

            self.minute_requests.append(now)
            self.daily_requests.append(now)


def create_demo_rate_limiter() -> DemoRateLimiter:
    return DemoRateLimiter(
        per_minute=int(
            os.environ.get("AI_DEMO_REQUESTS_PER_MINUTE", "5")
        ),
        per_day=int(
            os.environ.get("AI_DEMO_REQUESTS_PER_DAY", "100")
        ),
    )
