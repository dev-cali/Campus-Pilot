"""Shared database configuration without embedded credentials."""

import os


def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if not url:
        raise RuntimeError("DATABASE_URL must be set in the server environment.")
    return url
