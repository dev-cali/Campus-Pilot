
"""Server-to-server authentication for the fictional AI demo."""

import os
import secrets

from fastapi import Header, HTTPException


def require_demo_secret(
    x_ai_demo_secret: str | None = Header(default=None),
) -> None:
    """Reject unauthorized requests before the answer service runs."""

    expected = os.environ.get("AI_DEMO_SHARED_SECRET", "")

    # Fail closed when the server secret is missing or too short.
    if len(expected.strip()) < 32:
        raise HTTPException(
            status_code=503,
            detail="AI service access is not configured.",
        )

    supplied = x_ai_demo_secret or ""

    if not secrets.compare_digest(
        supplied.encode("utf-8"),
        expected.encode("utf-8"),
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized AI request.",
        )
