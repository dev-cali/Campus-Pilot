
"""Offline tests for AI demo rate limits."""

import unittest

from unittest.mock import patch

from fastapi import HTTPException

from ai.demo_rate_limit import DemoRateLimiter


class TestDemoRateLimiter(unittest.TestCase):

    def test_minute_limit(self):
        limiter = DemoRateLimiter(
            per_minute=2,
            per_day=10,
        )

        with patch(
            "ai.demo_rate_limit.time.monotonic",
            return_value=100.0,
        ):
            limiter.check()
            limiter.check()

            with self.assertRaises(HTTPException) as error:
                limiter.check()

            self.assertEqual(error.exception.status_code, 429)

    def test_daily_limit(self):
        limiter = DemoRateLimiter(
            per_minute=5,
            per_day=3,
        )

        with patch(
            "ai.demo_rate_limit.time.monotonic",
            return_value=100.0,
        ):
            for _ in range(3):
                limiter.check()

            with self.assertRaises(HTTPException) as error:
                limiter.check()

            self.assertEqual(error.exception.status_code, 429)

    def test_minute_window_expires(self):
        limiter = DemoRateLimiter(
            per_minute=1,
            per_day=10,
        )

        with patch(
            "ai.demo_rate_limit.time.monotonic",
            return_value=100.0,
        ):
            limiter.check()

            with self.assertRaises(HTTPException):
                limiter.check()

        with patch(
            "ai.demo_rate_limit.time.monotonic",
            return_value=160.0,
        ):
            limiter.check()

        self.assertEqual(len(limiter.minute_requests), 1)
        self.assertEqual(len(limiter.daily_requests), 2)

    def test_daily_window_expires(self):
        limiter = DemoRateLimiter(
            per_minute=5,
            per_day=1,
        )

        with patch(
            "ai.demo_rate_limit.time.monotonic",
            return_value=100.0,
        ):
            limiter.check()

        with patch(
            "ai.demo_rate_limit.time.monotonic",
            return_value=86500.0,
        ):
            limiter.check()

        self.assertEqual(len(limiter.daily_requests), 1)

    def test_minute_expiration_preserves_daily_quota(self):
        limiter = DemoRateLimiter(
            per_minute=1,
            per_day=1,
        )

        with patch(
            "ai.demo_rate_limit.time.monotonic",
            return_value=100.0,
        ):
            limiter.check()

        with patch(
            "ai.demo_rate_limit.time.monotonic",
            return_value=160.0,
        ):
            with self.assertRaises(HTTPException) as error:
                limiter.check()

            self.assertEqual(error.exception.status_code, 429)

    def test_invalid_limits(self):
        with self.assertRaises(ValueError):
            DemoRateLimiter(per_minute=0, per_day=100)

        with self.assertRaises(ValueError):
            DemoRateLimiter(per_minute=5, per_day=0)


if __name__ == "__main__":
    unittest.main()
