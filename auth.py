"""Bearer-token authentication and authorization for the CampusPilot API.

Supabase Auth owns identities: it stores accounts, runs the login and SSO
flows, and issues the access token the frontend sends as
``Authorization: Bearer <token>``. This module only verifies that token and
maps it onto a row in the project's own ``users`` table, so protected requests
do not depend on Supabase being reachable.

Configuration is read lazily, the same way ``database.py`` reads
``DATABASE_URL``, so importing the app never requires secrets. Missing
configuration fails closed: protected routes answer 503 rather than allowing
anonymous access.
"""

import os
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import User, get_db

# Supabase signs access tokens with HS256 using the project's JWT secret. The
# audience for a signed-in user is always "authenticated"; the token's `role`
# claim is the Postgres role, not an application role, so authorization comes
# from `users.role` instead.
ALGORITHM = "HS256"
AUDIENCE = "authenticated"
SECRET_ENV = "SUPABASE_JWT_SECRET"
ISSUER_ENV = "SUPABASE_JWT_ISSUER"

# Roles allowed to change data. `users.role` is free text today, so compare
# case-insensitively and tolerate surrounding whitespace.
STAFF_ROLES = frozenset({"staff", "admin"})

bearer_scheme = HTTPBearer(auto_error=False)


def _unauthorized(detail: str = "Invalid or missing authentication token.") -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )


def decode_access_token(token: str) -> dict:
    """Verify a Supabase access token and return its claims.

    Raises 503 when the server has no signing secret and 401 for every other
    failure. The algorithm list is explicit: trusting the token's own `alg`
    header would accept unsigned ("none") tokens and RS256-to-HS256 confusion.
    """
    secret = os.environ.get(SECRET_ENV)
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication is not configured on this server.",
        )

    issuer = os.environ.get(ISSUER_ENV) or None
    try:
        return jwt.decode(
            token,
            secret,
            algorithms=[ALGORITHM],
            audience=AUDIENCE,
            issuer=issuer,
            # A token without these claims is not a usable access token.
            options={"require": ["exp", "sub", "aud"]},
        )
    except jwt.InvalidTokenError:
        # Expired, forged, malformed and wrong-audience tokens are
        # deliberately indistinguishable to the caller.
        raise _unauthorized()


def get_token_claims(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> dict:
    """Verify the bearer token before anything touches the database.

    Keeping this separate from the user lookup means an unauthenticated request
    is rejected even when the database is unavailable, and bad tokens never
    cause a connection to be opened.
    """
    if credentials is None:
        raise _unauthorized("Authentication is required.")
    return decode_access_token(credentials.credentials)


def get_current_user(
    claims: dict = Depends(get_token_claims),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the caller to a local user, or raise 401.

    The token proves the email; the `users` table decides whether that person is
    allowed in this system at all. Emails are unique, so the match is 1:1.
    """
    email = claims.get("email")
    if not isinstance(email, str) or not email.strip():
        raise _unauthorized("The token does not identify an email address.")

    user = (
        db.query(User)
        .filter(func.lower(User.email) == email.strip().lower())
        .first()
    )
    if user is None:
        raise _unauthorized("No CampusPilot account matches this identity.")
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    """Allow only staff/admin accounts; students get 403."""
    if (user.role or "").strip().lower() not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a staff account.",
        )
    return user
