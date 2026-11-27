"""Shared Supabase access-token verification; independent of the application database."""

import os
from functools import lru_cache
from typing import Optional
from urllib.parse import urlparse

import httpx
import jwt
from jwt import PyJWKClient
from jwt.exceptions import PyJWKClientConnectionError, PyJWKClientError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

AUDIENCE = "authenticated"
SUPABASE_URL_ENV = "SUPABASE_URL"
SUPABASE_KEY_ENV = "SUPABASE_PUBLISHABLE_KEY"
REQUIRED_CLAIMS = ["exp", "sub", "aud", "iss", "role"]

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Invalid or missing authentication token.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _unavailable() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="Authentication verification is temporarily unavailable.",
    )


def _get_supabase_url() -> str:
    url = os.environ.get(SUPABASE_URL_ENV, "").strip().rstrip("/")
    if not url:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on this server.",
        )
    try:
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.path not in ("", "/")
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
        ):
            raise _unavailable()
    except ValueError:
        raise _unavailable()
    return url


def _get_publishable_key() -> str:
    key = os.environ.get(SUPABASE_KEY_ENV, "").strip()
    if not key:
        raise HTTPException(
            status_code=503,
            detail="Authentication is not configured on this server.",
        )
    return key


@lru_cache(maxsize=4)
def _get_jwks_client(jwks_url: str) -> PyJWKClient:
    return PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=300, timeout=5)


def _verify_es256(token: str) -> dict:
    issuer = f"{_get_supabase_url()}/auth/v1"
    jwks_url = f"{issuer}/.well-known/jwks.json"
    try:
        signing_key = _get_jwks_client(jwks_url).get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256"],
            audience=AUDIENCE,
            issuer=issuer,
            options={"require": REQUIRED_CLAIMS},
        )
    except PyJWKClientConnectionError:
        raise _unavailable()
    except (PyJWKClientError, jwt.InvalidTokenError):
        raise _unauthorized()


def _verify_hs256(token: str) -> dict:
    # Supabase Auth verifies the legacy token's signature and validity.
    issuer = f"{_get_supabase_url()}/auth/v1"
    try:
        response = httpx.get(
            f"{issuer}/user",
            headers={
                "apikey": _get_publishable_key(),
                "Authorization": f"Bearer {token}",
            },
            timeout=5,
            follow_redirects=False,
        )
    except httpx.RequestError:
        raise _unavailable()

    if response.status_code in (400, 401, 403):
        raise _unauthorized()
    if response.status_code != 200:
        raise _unavailable()

    try:
        user = response.json()
    except ValueError:
        raise _unavailable()
    if not isinstance(user, dict) or not isinstance(user.get("id"), str):
        raise _unauthorized()

    # Only after successful remote signature verification, enforce local claims.
    try:
        claims = jwt.decode(
            token,
            audience=AUDIENCE,
            issuer=issuer,
            options={
                "verify_signature": False,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_aud": True,
                "verify_iss": True,
                "verify_sub": True,
                "require": REQUIRED_CLAIMS,
            },
        )
    except jwt.InvalidTokenError:
        raise _unauthorized()

    if claims.get("sub") != user["id"] or user.get("is_anonymous") is True:
        raise _unauthorized()

    # Prefer the identity returned by the verified Supabase user endpoint.
    claims.pop("email", None)
    if isinstance(user.get("email"), str):
        claims["email"] = user["email"]
    return claims


def decode_access_token(token: str) -> dict:
    try:
        header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        raise _unauthorized()

    algorithm = header.get("alg")
    if algorithm == "ES256":
        claims = _verify_es256(token)
    elif algorithm == "HS256":
        claims = _verify_hs256(token)
    else:
        raise _unauthorized()

    subject = claims.get("sub")
    if (
        not isinstance(subject, str)
        or not subject.strip()
        or claims.get("role") != "authenticated"
        or claims.get("is_anonymous", False) is not False
    ):
        raise _unauthorized()
    return claims


def get_token_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise _unauthorized("Authentication is required.")
    return decode_access_token(credentials.credentials)
