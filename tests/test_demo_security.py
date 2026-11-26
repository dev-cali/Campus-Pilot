
"""Offline security tests for the fictional AI demo."""

import os
import unittest

from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from ai.demo_api import create_app


TEST_SECRET = "a" * 64


class TestDemoSecurity(unittest.TestCase):

    def setUp(self):
        self.environment = patch.dict(
            os.environ,
            {
                "AI_DEMO_SHARED_SECRET": TEST_SECRET,
                "AI_DEMO_REQUESTS_PER_MINUTE": "2",
                "AI_DEMO_REQUESTS_PER_DAY": "5",
            },
        )

        self.environment.start()
        self.addCleanup(self.environment.stop)

        self.service = Mock()

        self.service.ask.return_value = Mock(
            status="unavailable"
        )

        self.service.ask.return_value.model_dump.return_value = {
            "status": "unavailable"
        }

        self.app = create_app(service=self.service)
        self.client = TestClient(self.app)
        self.addCleanup(self.client.close)

        self.question = {
            "question": "What do fictional learners review?"
        }

        self.headers = {
            "X-AI-Demo-Secret": TEST_SECRET
        }

    def test_missing_secret(self):
        response = self.client.post(
            "/api/ai/ask",
            json=self.question,
        )

        self.assertEqual(response.status_code, 401)
        self.service.ask.assert_not_called()

    def test_incorrect_secret(self):
        response = self.client.post(
            "/api/ai/ask",
            json=self.question,
            headers={"X-AI-Demo-Secret": "incorrect"},
        )

        self.assertEqual(response.status_code, 401)
        self.service.ask.assert_not_called()

    def test_missing_server_configuration(self):
        with patch.dict(
            os.environ,
            {"AI_DEMO_SHARED_SECRET": ""},
        ):
            response = self.client.post(
                "/api/ai/ask",
                json=self.question,
                headers=self.headers,
            )

        self.assertEqual(response.status_code, 503)
        self.service.ask.assert_not_called()

    def test_valid_secret_reaches_service(self):
        response = self.client.post(
            "/api/ai/ask",
            json=self.question,
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 503)
        self.service.ask.assert_called_once()

    def test_minute_rate_limit(self):
        for _ in range(2):
            response = self.client.post(
                "/api/ai/ask",
                json=self.question,
                headers=self.headers,
            )

            self.assertEqual(response.status_code, 503)

        response = self.client.post(
            "/api/ai/ask",
            json=self.question,
            headers=self.headers,
        )

        self.assertEqual(response.status_code, 429)
        self.assertEqual(self.service.ask.call_count, 2)

    def test_unauthorized_requests_do_not_use_quota(self):
        for _ in range(5):
            response = self.client.post(
                "/api/ai/ask",
                json=self.question,
            )

            self.assertEqual(response.status_code, 401)

        for _ in range(2):
            response = self.client.post(
                "/api/ai/ask",
                json=self.question,
                headers=self.headers,
            )

            self.assertEqual(response.status_code, 503)

        self.assertEqual(self.service.ask.call_count, 2)


if __name__ == "__main__":
    unittest.main()
