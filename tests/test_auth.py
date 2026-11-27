
"""Authentication and authorization checks.

Everything here is offline: access tokens are minted with a throwaway test
secret, so no Supabase project, network call or paid provider call is involved.
"""

import base64
import json
import os
import tempfile
import time
import unittest
from unittest.mock import patch

from types import SimpleNamespace
from cryptography.hazmat.primitives.asymmetric import ec
from jwt.exceptions import PyJWKClientConnectionError
import httpx
import jwt
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import main
from database import Base, Department, User, get_db
from main import app


SECRET = "unit-test-supabase-secret-long-enough-for-hs256"

SUPABASE_URL = "https://test-project.supabase.co"
SUPABASE_ISSUER = f"{SUPABASE_URL}/auth/v1"
PUBLISHABLE_KEY = "test-publishable-key"

STAFF_EMAIL = "staff@example.test"
STUDENT_EMAIL = "student@example.test"


def _segment(value: dict) -> str:
    raw = json.dumps(value, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _unsigned_token(payload: dict) -> str:
    """A token with alg=none: the classic 'just trust me' forgery attempt."""
    return (
        _segment({"alg": "none", "typ": "JWT"})
        + "."
        + _segment(payload)
        + "."
    )


def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

class UnavailableJwksClient:
    def get_signing_key_from_jwt(self, token):
        raise PyJWKClientConnectionError(
            "JWKS endpoint unavailable"
        )

class AuthTests(unittest.TestCase):

    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(self.db_fd)

        self.engine = create_engine(
            "sqlite:///" + self.db_path,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        # Generate temporary ECC P-256 keys for ES256 tests.
        self.es256_private_key = ec.generate_private_key(
            ec.SECP256R1()
        )

        self.es256_public_key = (
            self.es256_private_key.public_key()
        )

        event.listen(
            self.engine,
            "connect",
            _enable_sqlite_foreign_keys,
        )

        Base.metadata.create_all(bind=self.engine)

        self.Session = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

        session = self.Session()

        staff = User(
            name="Staff Member",
            email=STAFF_EMAIL,
            role="staff",
        )

        student = User(
            name="Student Member",
            email=STUDENT_EMAIL,
            role="student",
        )

        department = Department(name="Test Department")

        session.add_all([staff, student, department])
        session.commit()

        self.staff_id = staff.id
        self.student_id = student.id
        self.department_id = department.id

        session.close()

        def override_get_db():
            db = self.Session()

            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db

        self.client = TestClient(app)

        # Configure Supabase environment variables for offline tests.
        environment = patch.dict(
            os.environ,
            {
                "SUPABASE_URL": SUPABASE_URL,
                "SUPABASE_PUBLISHABLE_KEY": PUBLISHABLE_KEY,
            },
        )

        environment.start()
        self.addCleanup(environment.stop)

        # Mock Supabase Auth's /user endpoint.
        supabase_mock = patch(
            "auth_tokens.httpx.get",
            side_effect=self._mock_supabase_user_lookup,
        )

        supabase_mock.start()
        self.addCleanup(supabase_mock.stop)

        self.addCleanup(self._cleanup)

    def _mock_supabase_user_lookup(
        self,
        url,
        *,
        headers,
        timeout,
        follow_redirects,
    ):
        """Simulate Supabase Auth token verification without network access."""

        self.assertEqual(
            url,
            f"{SUPABASE_URL}/auth/v1/user",
        )

        self.assertEqual(
            headers["apikey"],
            PUBLISHABLE_KEY,
        )

        token = headers["Authorization"].removeprefix("Bearer ")

        request = httpx.Request("GET", url)

        try:
            claims = jwt.decode(
                token,
                SECRET,
                algorithms=["HS256"],
                audience="authenticated",
                issuer=SUPABASE_ISSUER,
                options={
                    "require": ["exp", "sub", "aud", "iss"]
                },
            )

        except jwt.InvalidTokenError:
            return httpx.Response(
                401,
                request=request,
            )

        return httpx.Response(
            200,
            json={
                "id": claims["sub"],
                "email": claims.get("email"),
            },
            request=request,
        )

    def _cleanup(self):
        app.dependency_overrides = {}
        self.client.close()
        self.engine.dispose()
        os.unlink(self.db_path)

    def token(
        self,
        email=STAFF_EMAIL,
        *,
        secret=SECRET,
        expires_in=300,
        audience="authenticated",
        algorithm="HS256",
    ):
        payload = {
            "sub": "11111111-1111-1111-1111-111111111111",
            "email": email,
            "role": "authenticated",
            "aud": audience,
            "iss": SUPABASE_ISSUER,
            "exp": int(time.time()) + expires_in,
        }

        return jwt.encode(
            payload,
            secret,
            algorithm=algorithm,
        )


    def es256_token(
        self,
        email=STAFF_EMAIL,
        *,
        private_key=None,
        expires_in=300,
        audience="authenticated",
        issuer=SUPABASE_ISSUER,
    ):
        payload = {
            "sub": "11111111-1111-1111-1111-111111111111",
            "email": email,
            "role": "authenticated",
            "aud": audience,
            "iss": issuer,
            "exp": int(time.time()) + expires_in,
        }

        signing_key = private_key or self.es256_private_key

        return jwt.encode(
            payload,
            signing_key,
            algorithm="ES256",
            headers={"kid": "test-es256-key"},
        )

    def _mock_jwks(self):
        signing_key = SimpleNamespace(
            key=self.es256_public_key
        )

        jwks_client = SimpleNamespace(
            get_signing_key_from_jwt=lambda token: signing_key
        )

        def client_factory(jwks_url):
            self.assertEqual(
                jwks_url,
                f"{SUPABASE_ISSUER}/.well-known/jwks.json",
            )

            return jwks_client

        return patch(
            "auth_tokens._get_jwks_client",
            side_effect=client_factory,
        )

    def auth(self, email=STAFF_EMAIL, **kwargs):
        return {
            "Authorization": "Bearer "
            + self.token(email, **kwargs)
        }

    # --- public surface -------------------------------------------------

    def test_health_endpoint_stays_public(self):
        self.assertEqual(
            self.client.get("/").status_code,
            200,
        )

    def test_reference_data_requires_authentication(self):
        response = self.client.get("/departments")

        self.assertEqual(response.status_code, 401)

        self.assertIn(
            "bearer",
            response.headers.get("www-authenticate", "").lower(),
        )

    # --- token rejection -------------------------------------------------

    def test_malformed_token_is_rejected(self):
        response = self.client.get(
            "/departments",
            headers={"Authorization": "Bearer not-a-jwt"},
        )

        self.assertEqual(response.status_code, 401)

    def test_non_bearer_scheme_is_rejected(self):
        response = self.client.get(
            "/departments",
            headers={"Authorization": "Basic dXNlcjpwYXNz"},
        )

        self.assertEqual(response.status_code, 401)

    def test_expired_token_is_rejected(self):
        response = self.client.get(
            "/departments",
            headers=self.auth(expires_in=-1),
        )

        self.assertEqual(response.status_code, 401)

    def test_token_signed_with_another_secret_is_rejected(self):
        response = self.client.get(
            "/departments",
            headers=self.auth(
                secret="not-the-project-secret-but-long-enough"
            ),
        )

        self.assertEqual(response.status_code, 401)

    def test_unsigned_token_is_rejected(self):
        payload = {
            "sub": "11111111-1111-1111-1111-111111111111",
            "email": STAFF_EMAIL,
            "role": "authenticated",
            "aud": "authenticated",
            "exp": int(time.time()) + 300,
        }

        response = self.client.get(
            "/departments",
            headers={
                "Authorization": "Bearer " + _unsigned_token(payload)
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_wrong_audience_is_rejected(self):
        response = self.client.get(
            "/departments",
            headers=self.auth(audience="anon"),
        )

        self.assertEqual(response.status_code, 401)

    def test_token_without_an_expiry_is_rejected(self):
        token = jwt.encode(
            {
                "sub": "11111111-1111-1111-1111-111111111111",
                "email": STAFF_EMAIL,
                "role": "authenticated",
                "aud": "authenticated",
                "iss": SUPABASE_ISSUER,
            },
            SECRET,
            algorithm="HS256",
        )

        response = self.client.get(
            "/departments",
            headers={"Authorization": "Bearer " + token},
        )

        self.assertEqual(response.status_code, 401)

    def test_identity_without_a_local_account_is_rejected(self):
        response = self.client.get(
            "/departments",
            headers=self.auth("nobody@example.test"),
        )

        self.assertEqual(response.status_code, 401)

    def test_missing_supabase_url_fails_closed(self):
        headers = self.auth()

        with patch.dict(os.environ, {"SUPABASE_URL": ""}):
            response = self.client.get(
                "/departments",
                headers=headers,
            )

        self.assertEqual(response.status_code, 503)

    def test_missing_token_is_rejected_before_the_database_is_used(self):
        def unavailable_database():
            raise RuntimeError("database is unavailable")
            yield  # pragma: no cover - only reached if dependency runs

        app.dependency_overrides[get_db] = unavailable_database

        # A 500 here would mean authentication waited for a database session.
        response = self.client.get("/departments")

        self.assertEqual(response.status_code, 401)

    # --- role checks ------------------------------------------------------

    def test_email_match_ignores_case(self):
        headers = {
            "Authorization": "Bearer "
            + self.token(STAFF_EMAIL.upper())
        }

        response = self.client.get(
            "/departments",
            headers=headers,
        )

        self.assertEqual(response.status_code, 200)

    def test_student_can_read_documents(self):
        response = self.client.get(
            "/documents/",
            headers=self.auth(STUDENT_EMAIL),
        )

        self.assertEqual(response.status_code, 200)

    def test_student_cannot_list_users(self):
        response = self.client.get(
            "/users/",
            headers=self.auth(STUDENT_EMAIL),
        )

        self.assertEqual(response.status_code, 403)

    def test_student_cannot_create_documents(self):
        response = self.client.post(
            "/documents/",
            json={
                "department_id": self.department_id,
                "title": "Unauthorised",
                "version": "1",
                "effective_date": "2026-01-01",
                "status": "draft",
            },
            headers=self.auth(STUDENT_EMAIL),
        )

        self.assertEqual(response.status_code, 403)

    def test_student_cannot_ingest_chunks(self):
        response = self.client.post(
            "/ingest/chunk",
            json={
                "document_id": 1,
                "page_no": 1,
                "text": "text",
                "source_reference": "page 1",
            },
            headers=self.auth(STUDENT_EMAIL),
        )

        self.assertEqual(response.status_code, 403)

    def test_staff_can_create_a_user(self):
        response = self.client.post(
            "/users/",
            json={
                "name": "New Staff",
                "email": "new.staff@example.test",
                "role": "staff",
            },
            headers=self.auth(),
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["email"],
            "new.staff@example.test",
        )

    def test_admin_role_is_accepted_on_staff_routes(self):
        session = self.Session()

        session.add(
            User(
                name="Admin",
                email="admin@example.test",
                role="admin",
            )
        )

        session.commit()
        session.close()

        response = self.client.get(
            "/users/",
            headers=self.auth("admin@example.test"),
        )

        self.assertEqual(response.status_code, 200)

    def test_student_question_is_recorded_against_their_own_account(self):
        response = self.client.post(
            "/questions/",
            json={
                # A student may not attribute a question to somebody else.
                "user_id": self.staff_id,
                "department_id": self.department_id,
                "query": "What is the deadline?",
                "answer": "Friday.",
            },
            headers=self.auth(STUDENT_EMAIL),
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["user_id"],
            self.student_id,
        )

    def test_staff_can_record_a_question_for_another_user(self):
        response = self.client.post(
            "/questions/",
            json={
                "user_id": self.student_id,
                "department_id": self.department_id,
                "query": "What is the deadline?",
                "answer": "Friday.",
            },
            headers=self.auth(),
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.json()["user_id"],
            self.student_id,
        )

    # --- /test-ai ---------------------------------------------------------

    def test_test_ai_requires_authentication_before_calling_the_provider(self):
        with patch("main.OpenAI") as openai_client:
            response = self.client.get("/test-ai")

        self.assertEqual(response.status_code, 401)
        openai_client.assert_not_called()

    def test_test_ai_rejects_students(self):
        with patch("main.OpenAI") as openai_client:
            response = self.client.get(
                "/test-ai",
                headers=self.auth(STUDENT_EMAIL),
            )

        self.assertEqual(response.status_code, 403)
        openai_client.assert_not_called()

    def test_test_ai_hides_provider_error_details(self):
        with patch.dict(os.environ, {"AI_API_KEY": "test-key"}), patch(
            "main.OpenAI"
        ) as openai_client:

            openai_client.return_value.chat.completions.create.side_effect = (
                RuntimeError("provider secret detail")
            )

            response = self.client.get(
                "/test-ai",
                headers=self.auth(),
            )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("provider secret detail", response.text)
        self.assertNotIn("RuntimeError", response.text)

    def test_test_ai_without_a_key_returns_a_neutral_error(self):
        with patch.dict(os.environ, {"AI_API_KEY": ""}):
            response = self.client.get(
                "/test-ai",
                headers=self.auth(),
            )

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("AI_API_KEY", response.text)

    # --- ES256 / JWKS verification --------------------------------------

    def test_es256_valid_token_is_accepted(self):
        token = self.es256_token()

        with self._mock_jwks():
            response = self.client.get(
                "/departments",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        self.assertEqual(response.status_code, 200)

    def test_es256_forged_signature_is_rejected(self):
        attacker_key = ec.generate_private_key(
            ec.SECP256R1()
        )

        token = self.es256_token(
            private_key=attacker_key
        )

        with self._mock_jwks():
            response = self.client.get(
                "/departments",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_es256_expired_token_is_rejected(self):
        token = self.es256_token(expires_in=-1)

        with self._mock_jwks():
            response = self.client.get(
                "/departments",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_es256_wrong_issuer_is_rejected(self):
        token = self.es256_token(
            issuer="https://attacker.example/auth/v1"
        )

        with self._mock_jwks():
            response = self.client.get(
                "/departments",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_es256_wrong_audience_is_rejected(self):
        token = self.es256_token(
            audience="anon"
        )

        with self._mock_jwks():
            response = self.client.get(
                "/departments",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        self.assertEqual(response.status_code, 401)

    def test_es256_jwks_unavailable_fails_closed(self):
        token = self.es256_token()

        with patch(
            "auth_tokens._get_jwks_client",
            return_value=UnavailableJwksClient(),
        ):
            response = self.client.get(
                "/departments",
                headers={
                    "Authorization": f"Bearer {token}"
                },
            )

        self.assertEqual(response.status_code, 503)

    # --- CORS -------------------------------------------------------------

    def test_cors_allows_the_configured_origin(self):
        response = self.client.options(
            "/departments",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.headers.get("access-control-allow-origin"),
            "http://localhost:3000",
        )

    def test_cors_rejects_an_unknown_origin(self):
        response = self.client.options(
            "/departments",
            headers={
                "Origin": "https://evil.example",
                "Access-Control-Request-Method": "GET",
            },
        )

        self.assertEqual(response.status_code, 400)

        self.assertIsNone(
            response.headers.get("access-control-allow-origin")
        )

    def test_allowed_origins_are_parsed_from_the_environment(self):
        with patch.dict(
            os.environ,
            {
                "ALLOWED_ORIGINS": (
                    " https://a.example , ,https://b.example "
                )
            },
        ):
            self.assertEqual(
                main.get_allowed_origins(),
                ["https://a.example", "https://b.example"],
            )


if __name__ == "__main__":
    unittest.main()
