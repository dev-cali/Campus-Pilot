"""Temporary local SQLite tests. No shared database or external service access."""

import copy
import tempfile
import unittest
from datetime import date
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai.demo_store import DEFAULT_FIXTURE, DemoChunk, DemoDocument, DemoStore
from ai.document_eligibility import load_fictional_documents


REFERENCE_DATE = date(2026, 10, 26)


class DemoStoreTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = DemoStore(Path(self.directory.name) / "demo.sqlite3")
        self.addCleanup(self.store.close)
        self.store.initialize()
        self.documents = load_fictional_documents(DEFAULT_FIXTURE)

    def counts(self):
        with Session(self.store.engine) as session:
            return (
                session.scalar(select(func.count()).select_from(DemoDocument)),
                session.scalar(select(func.count()).select_from(DemoChunk)),
            )

    def test_seed_is_repeatable_and_round_trips_all_metadata(self):
        for _ in range(2):
            self.assertEqual(self.store.seed(self.documents, reference_date=REFERENCE_DATE), (6, 3))
            self.assertEqual(self.counts(), (6, 3))
        self.assertEqual(self.store.load_documents(), self.documents)

    def test_only_public_eligible_chunks_are_stored_and_returned(self):
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        with Session(self.store.engine) as session:
            self.assertEqual(set(session.scalars(select(DemoChunk.document_id))), {101, 103})
        chunks = self.store.public_chunks(reference_date=REFERENCE_DATE)
        self.assertEqual([(c.document_id, c.page_no, c.version) for c in chunks],
                         [(101, 1, "v2"), (101, 2, "v2"), (103, 1, "v1")])
        self.assertEqual(chunks[0].source_reference, self.documents[0]["source_reference"])

    def test_invalid_seed_preserves_existing_catalog(self):
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        bad = copy.deepcopy(self.documents)
        del bad[-1]["status"]
        with self.assertRaisesRegex(ValueError, "^invalid_demo_catalog$"):
            self.store.seed(bad, reference_date=REFERENCE_DATE)
        self.assertEqual(self.store.load_documents(), self.documents)
        self.assertEqual(self.counts(), (6, 3))

    def test_reseed_revocation_removes_old_chunks(self):
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        self.documents[0]["status"] = "revoked"
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        self.assertEqual(self.counts(), (6, 1))
        self.assertEqual({c.document_id for c in self.store.public_chunks(reference_date=REFERENCE_DATE)}, {103})

    def test_read_revalidates_metadata_instead_of_trusting_chunk_snapshot(self):
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        with Session(self.store.engine) as session, session.begin():
            row = session.get(DemoDocument, 101)
            changed = dict(row.record)
            changed["access_level"] = "staff"
            row.record = changed
        self.assertEqual(self.counts(), (6, 3))  # Old snapshot still exists.
        self.assertEqual({c.document_id for c in self.store.public_chunks(reference_date=REFERENCE_DATE)}, {103})

    def test_future_date_is_rechecked_when_reading(self):
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        self.assertEqual(self.store.public_chunks(reference_date=date(2020, 1, 1)), ())

    def test_foreign_key_prevents_orphan_chunk(self):
        with self.assertRaises(IntegrityError):
            with Session(self.store.engine) as session, session.begin():
                session.add(DemoChunk(document_id=999, page_no=1, chunk_index=0,
                                      chunk_text="Fictional", start_char=0, end_char=9))

    def test_invalid_database_record_fails_closed(self):
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        with Session(self.store.engine) as session, session.begin():
            session.get(DemoDocument, 101).record = {"document_id": 999}
        with self.assertRaisesRegex(ValueError, "^invalid_demo_catalog$"):
            self.store.public_chunks(reference_date=REFERENCE_DATE)

    def test_reseed_removes_deleted_fixture_documents(self):
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        remaining = [record for record in self.documents if record["document_id"] != 103]
        self.store.seed(remaining, reference_date=REFERENCE_DATE)
        self.assertEqual(self.counts(), (5, 2))

    def test_empty_store_returns_no_evidence(self):
        self.assertEqual(self.store.public_chunks(reference_date=REFERENCE_DATE), ())


if __name__ == "__main__":
    unittest.main()
