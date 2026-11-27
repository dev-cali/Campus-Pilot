"""CampusPilot database authorization and role permissions."""

from fastapi import Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from database import User, get_db

from auth_tokens import (
    _unauthorized,
    decode_access_token,
    get_token_claims,
)


STAFF_ROLES = frozenset({"staff", "admin"})


def get_current_user(
    claims: dict = Depends(get_token_claims),
    db: Session = Depends(get_db),
) -> User:
    """Resolve the verified identity to a local CampusPilot user."""
    email = claims.get("email")

    if not isinstance(email, str) or not email.strip():
        raise _unauthorized(
            "The token does not identify an email address."
        )

    user = (
        db.query(User)
        .filter(
            func.lower(User.email) == email.strip().lower()
        )
        .first()
    )

    if user is None:
        raise _unauthorized(
            "No CampusPilot account matches this identity."
        )

    return user


def require_staff(
    user: User = Depends(get_current_user),
) -> User:
    """Allow only staff/admin accounts; students get 403."""
    if (user.role or "").strip().lower() not in STAFF_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This action requires a staff account.",
        )

    return user
