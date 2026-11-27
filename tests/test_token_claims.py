"""Offline checks for authenticated-user claims and legacy token validation."""

import os
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import HTTPException

import auth_tokens


URL = "https://test-project.supabase.co"
ISSUER = f"{URL}/auth/v1"
SUBJECT = "11111111-1111-1111-1111-111111111111"
SECRET = "fictional-test-signing-secret-at-least-32-characters"


class TokenClaimsTests(unittest.TestCase):
    def setUp(self):
        env = patch.dict(os.environ, {
            "SUPABASE_URL": URL,
            "SUPABASE_PUBLISHABLE_KEY": "fictional-publishable-key",
        })
        env.start()
        self.addCleanup(env.stop)
        self.private_key = ec.generate_private_key(ec.SECP256R1())

    def claims(self, **overrides):
        return {
            "sub": SUBJECT,
            "iss": ISSUER,
            "aud": "authenticated",
            "role": "authenticated",
            "exp": int(time.time()) + 300,
            **overrides,
        }

    def es256(self, claims):
        token = jwt.encode(claims, self.private_key, algorithm="ES256", headers={"kid": "test"})
        client = SimpleNamespace(get_signing_key_from_jwt=lambda _: SimpleNamespace(key=self.private_key.public_key()))
        with patch("auth_tokens._get_jwks_client", return_value=client):
            return auth_tokens.decode_access_token(token)

    def hs256(self, claims, **user_overrides):
        token = jwt.encode(claims, SECRET, algorithm="HS256")
        # Deliberately return 200 even for invalid claims, to independently
        # exercise the backend's local validation after remote verification.
        response = httpx.Response(200, json={"id": SUBJECT, "email": "test@example.test", **user_overrides})
        with patch("auth_tokens.httpx.get", return_value=response):
            return auth_tokens.decode_access_token(token)

    def assert_rejected(self, verify, claims, **kwargs):
        with self.assertRaises(HTTPException) as caught:
            verify(claims, **kwargs)
        self.assertEqual(caught.exception.status_code, 401)

    def test_es256_authenticated_user_accepted(self):
        self.assertEqual(self.es256(self.claims())["sub"], SUBJECT)

    def test_es256_anonymous_or_non_user_role_rejected(self):
        for overrides in ({"is_anonymous": True}, {"role": "anon"}, {"role": "service_role"}, {"sub": ""}):
            with self.subTest(overrides=overrides):
                self.assert_rejected(self.es256, self.claims(**overrides))

    def test_legacy_authenticated_user_accepted(self):
        self.assertEqual(self.hs256(self.claims())["sub"], SUBJECT)

    def test_legacy_invalid_claims_rejected_despite_remote_success(self):
        for overrides in ({"exp": 1}, {"aud": "wrong"}, {"iss": "https://wrong.example/auth/v1"}, {"role": "anon"}, {"is_anonymous": True}):
            with self.subTest(overrides=overrides):
                self.assert_rejected(self.hs256, self.claims(**overrides))
        for name in ("exp", "aud", "iss", "sub", "role"):
            claims = self.claims()
            del claims[name]
            with self.subTest(missing=name):
                self.assert_rejected(self.hs256, claims)

    def test_legacy_remote_identity_must_match(self):
        self.assert_rejected(self.hs256, self.claims(), id="different-user")
        self.assert_rejected(self.hs256, self.claims(), is_anonymous=True)


if __name__ == "__main__":
    unittest.main()
