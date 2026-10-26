"""Keyword retrieval tests using a temporary fictional SQLite database."""

import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock

from ai.demo_store import DEFAULT_FIXTURE, DemoStore
from ai.document_eligibility import load_fictional_documents
from ai.local_retrieval import KeywordRetriever, validate_question


REFERENCE_DATE = date(2026, 10, 26)


class LocalRetrievalTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = DemoStore(Path(directory.name) / "retrieval.sqlite3")
        self.addCleanup(self.store.close)
        self.store.initialize()
        self.documents = load_fictional_documents(DEFAULT_FIXTURE)
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        self.retriever = KeywordRetriever(self.store)

    def test_scholarship_candidates_keep_current_source_metadata(self):
        evidence = self.retriever.retrieve("Explain the scholarship practice form", reference_date=REFERENCE_DATE)
        self.assertEqual(len(evidence), 2)
        self.assertEqual({e.chunk.document_id for e in evidence}, {101})
        self.assertEqual({e.chunk.page_no for e in evidence}, {1, 2})
        self.assertEqual({e.chunk.version for e in evidence}, {"v2"})
        self.assertEqual([e.evidence_id for e in evidence], ["e1", "e2"])
        self.assertTrue(all(e.chunk.source_reference == self.documents[0]["source_reference"] for e in evidence))

    def test_no_match_and_generic_words_return_no_evidence(self):
        for question in ("interplanetary teleportation", "What is Demo Campus University?"):
            self.assertEqual(self.retriever.retrieve(question, reference_date=REFERENCE_DATE), ())

    def test_staff_draft_revoked_and_old_content_are_not_retrieved(self):
        for question in ("staff blue folders", "handbook", "lantern announcement", "retired old practice form"):
            evidence = self.retriever.retrieve(question, reference_date=REFERENCE_DATE)
            self.assertTrue(all(e.chunk.document_id in {101, 103} for e in evidence))
            self.assertNotIn("imaginary blue folders", repr(evidence))

    def test_retrieval_rechecks_revocation(self):
        self.assertTrue(self.retriever.retrieve("scholarship", reference_date=REFERENCE_DATE))
        self.documents[0]["status"] = "revoked"
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        self.assertEqual(self.retriever.retrieve("scholarship", reference_date=REFERENCE_DATE), ())

    def test_deterministic_bounded_order(self):
        retriever = KeywordRetriever(self.store, limit=1)
        first = retriever.retrieve("scholarship", reference_date=REFERENCE_DATE)
        self.assertEqual(first, retriever.retrieve("SCHOLARSHIP!", reference_date=REFERENCE_DATE))
        self.assertEqual(len(first), 1)
        self.assertEqual(first[0].chunk.page_no, 1)

    def test_invalid_question_never_reads_source(self):
        source = Mock()
        retriever = KeywordRetriever(source)
        for question in (None, True, [], "", "   ", "a" * 2001):
            with self.assertRaises(ValueError):
                retriever.retrieve(question, reference_date=REFERENCE_DATE)
        source.public_chunks.assert_not_called()
        self.assertEqual(validate_question(" hello "), "hello")
        self.assertEqual(len(validate_question("a" * 2000)), 2000)

    def test_invalid_limit_or_date_is_rejected(self):
        for limit in (True, 0, 6, "3"):
            with self.assertRaisesRegex(ValueError, "^invalid_retrieval_limit$"):
                KeywordRetriever(self.store, limit=limit)
        with self.assertRaisesRegex(ValueError, "^invalid_reference_date$"):
            self.retriever.retrieve("scholarship", reference_date="2026-10-26")

    def test_source_failure_is_not_disguised_as_missing_evidence(self):
        source = Mock()
        source.public_chunks.side_effect = ValueError("invalid_demo_catalog")
        with self.assertRaisesRegex(ValueError, "^invalid_demo_catalog$"):
            KeywordRetriever(source).retrieve("scholarship", reference_date=REFERENCE_DATE)


if __name__ == "__main__":
    unittest.main()
