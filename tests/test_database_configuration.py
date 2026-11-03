"""Offline checks using synthetic values and temporary SQLite only."""

import contextlib
import importlib.util
import io
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from database_config import get_database_url


ROOT = Path(__file__).resolve().parents[1]


class DatabaseConfigurationTests(unittest.TestCase):
    def test_missing_or_blank_url_fails_without_disclosing_values(self):
        for value in (None, "", "  "):
            with self.subTest(value=value), patch.dict(os.environ, {}, clear=True):
                if value is not None:
                    os.environ["DATABASE_URL"] = value
                with self.assertRaisesRegex(RuntimeError, "DATABASE_URL must be set"):
                    get_database_url()

    def test_encoded_password_preserved(self):
        url = "postgresql://fictional:fake%40pass%25@invalid.example/test"
        with patch.dict(os.environ, {"DATABASE_URL": url}):
            self.assertEqual(get_database_url(), url)

    def test_backend_uses_environment_without_connecting(self):
        result = subprocess.run(
            [sys.executable, "-B", "-c",
             "import database; assert database.get_engine().url.database == ':memory:'"],
            cwd=ROOT, env={**os.environ, "DATABASE_URL": "sqlite:///:memory:"},
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, "Backend environment configuration failed")

    @unittest.skipUnless(importlib.util.find_spec("alembic.config"), "Alembic unavailable")
    def test_alembic_offline_and_online_use_environment(self):
        from alembic import command
        from alembic.config import Config

        with tempfile.TemporaryDirectory() as directory:
            url = "sqlite:///" + (Path(directory) / "fake%25database.sqlite").as_posix()
            # The migration adds columns to document_chunks, so the online run
            # needs the pre-migration table to exist in the scratch database.
            # SQLAlchemy decodes %25 to % in the path, so that is the real file.
            scratch = sqlite3.connect(Path(directory) / "fake%database.sqlite")
            try:
                scratch.execute(
                    "CREATE TABLE document_chunks (id INTEGER PRIMARY KEY, "
                    "document_id INTEGER NOT NULL, page_no INTEGER NOT NULL, "
                    "chunk_text TEXT NOT NULL, embedding TEXT)"
                )
                scratch.commit()
            finally:
                scratch.close()
            with patch.dict(os.environ, {"DATABASE_URL": url}):
                for offline in (True, False):
                    with self.subTest(offline=offline):
                        config = Config(str(ROOT / "alembic.ini"))
                        config.set_main_option("script_location", str(ROOT / "alembic"))
                        # A stale config URL must never override the environment.
                        config.set_main_option("sqlalchemy.url", "invalid://ignored")
                        config.output_buffer = io.StringIO()
                        with contextlib.redirect_stdout(io.StringIO()):
                            command.upgrade(config, "head", sql=offline)


if __name__ == "__main__":
    unittest.main()
