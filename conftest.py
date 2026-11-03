import os

# Tests override the database dependency and use a temporary SQLite database.
# This URL is never connected to; it only lets database.py build its engine at import.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/test")
