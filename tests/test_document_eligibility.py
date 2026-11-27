"""Fictional offline tests; no backend imports, API calls, or credentials."""

import copy
import unittest
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from unittest.mock import patch

from ai.document_eligibility import (
    evaluate_documents, load_fictional_documents, process_documents,
    validate_document,
)
from ai.document_processing import normalize_document_text, split_document_text


FIXTURE = Path(__file__).parent / "fixtures" / "fictional_documents.json"
REFERENCE_DATE = date(2026, 10, 25)
EXPANDED_REFERENCE_DATE = date(2026, 11, 27)
LEGACY_DOCUMENT_IDS = set(range(101, 107))
EXPECTED_PUBLIC_DOCUMENT_IDS = {101, 103, 107, 108, 109, 110, 111, 112, 113}
EXPECTED_EXCLUDED_DOCUMENT_IDS = {102, 104, 105, 106}


class DocumentEligibilityTests(unittest.TestCase):
    def setUp(self):
        self.all_documents = load_fictional_documents(FIXTURE)
        # Keep the original six-record contract isolated for its existing tests.
        self.documents = [d for d in self.all_documents
                          if d["document_id"] in LEGACY_DOCUMENT_IDS]

    def evaluate(self, documents=None, **options):
        arguments = {"trusted_permissions": {"public"}, "reference_date": REFERENCE_DATE}
        arguments.update(options)
        return evaluate_documents(self.documents if documents is None else documents, **arguments)

    def process(self, **options):
        arguments = {"trusted_permissions": {"public"}, "reference_date": REFERENCE_DATE}
        arguments.update(options)
        return process_documents(self.documents, **arguments)

    def test_six_fictional_records_have_valid_metadata(self):
        self.assertEqual(len(self.documents), 6)
        for document in self.documents:
            self.assertTrue(validate_document(document).eligible)
            for page in document["pages"]:
                self.assertIn("FICTIONAL TEST DATA", page["text"])

    def test_expanded_catalog_preserves_legacy_records_and_exact_eligibility(self):
        self.assertEqual(len(self.all_documents), 13)
        self.assertEqual(self.all_documents[:6], self.documents)
        ids = [document["document_id"] for document in self.all_documents]
        references = [document["source_reference"] for document in self.all_documents]
        self.assertEqual(len(set(ids)), 13)
        self.assertEqual(set(ids), set(range(101, 114)))
        self.assertEqual(len(set(references)), 13)

        for document in self.all_documents:
            with self.subTest(document_id=document["document_id"]):
                self.assertTrue(validate_document(document).eligible)
                self.assertNotIn("category", document)
                self.assertEqual(document["fictional"], True)
                for page in document["pages"]:
                    self.assertTrue(page["text"].startswith("FICTIONAL TEST DATA."))
                    self.assertLessEqual(len(page["text"]), 1000)

        decisions = evaluate_documents(
            self.all_documents, trusted_permissions={"public"},
            reference_date=EXPANDED_REFERENCE_DATE,
        )
        eligible = {d["document_id"] for d, result in zip(self.all_documents, decisions)
                    if result.eligible}
        excluded = {d["document_id"] for d, result in zip(self.all_documents, decisions)
                    if not result.eligible}
        self.assertEqual(eligible, EXPECTED_PUBLIC_DOCUMENT_IDS)
        self.assertEqual(excluded, EXPECTED_EXCLUDED_DOCUMENT_IDS)
        self.assertEqual(decisions[1].reason, "superseded")
        self.assertEqual(decisions[4].reason, "access_denied")

    def test_approved_fictional_facts_are_consistent_across_documents(self):
        by_id = {d["document_id"]: " ".join(p["text"] for p in d["pages"])
                 for d in self.all_documents}
        self.assertIn("January 4, 2027", by_id[107])
        self.assertIn("January 11–15, 2027", by_id[107])
        self.assertIn("January 15", by_id[110])
        self.assertIn("December 11, 2026", by_id[109])
        self.assertIn("December 11", by_id[113])
        self.assertIn("1.75", by_id[109])
        self.assertIn("2.50", by_id[109])
        self.assertIn("3.00 is passing", by_id[111])
        self.assertIn("₱1,000 per unit", by_id[110])
        self.assertIn("₱21,000", by_id[110])
        self.assertIn("₱8,400", by_id[110])
        self.assertIn("₱6,300", by_id[110])
        self.assertEqual(8400 + 6300 + 6300, 21000)
        self.assertIn("Data Fundamentals, 3 units, requires passing Intro to Programming",
                      by_id[108])
        self.assertIn("no real enrollment requirements apply", by_id[111].casefold())
        self.assertIn("do not amend Document 101", by_id[109])
        self.assertIn("registrar@demo-campus.example", by_id[112])
        self.assertIn("registrar@demo-campus.example", by_id[113])

    def test_approved_public_accepted(self):
        decisions = self.evaluate()
        self.assertTrue(decisions[0].eligible)
        self.assertTrue(decisions[2].eligible)

    def test_draft_rejected(self):
        self.assertEqual(self.evaluate()[3].reason, "not_approved")

    def test_revoked_rejected(self):
        self.assertEqual(self.evaluate()[5].reason, "not_approved")

    def test_staff_only_rejected_for_public(self):
        self.assertEqual(self.evaluate()[4].reason, "access_denied")

    def test_staff_requires_explicit_grant(self):
        self.assertTrue(self.evaluate(trusted_permissions={"public", "staff"})[4].eligible)
        self.assertFalse(self.evaluate(trusted_permissions={"staff"})[0].eligible)
        for value in (None, "staff", ["staff"], {"department": "staff"}, set(), {"admin"}):
            with self.subTest(value=value):
                self.assertTrue(all(not d.eligible for d in self.evaluate(trusted_permissions=value)))

    def test_superseded_rejected(self):
        self.assertEqual(self.evaluate()[1].reason, "superseded")

    def test_replacement_link_overrides_stale_current_flag(self):
        self.documents[1]["version_state"] = "current"
        self.assertEqual(self.evaluate()[1].reason, "superseded")

    def test_future_effective_and_exact_boundary(self):
        self.documents[2]["effective_date"] = "2026-10-26"
        self.assertEqual(self.evaluate()[2].reason, "not_yet_effective")
        self.assertTrue(self.evaluate(reference_date=date(2026, 10, 26))[2].eligible)

    def test_missing_required_fields_fail_closed(self):
        for field in self.documents[0]:
            if field == "supersedes":
                continue
            document = copy.deepcopy(self.documents[0])
            del document[field]
            with self.subTest(field=field):
                self.assertFalse(validate_document(document).eligible)
                self.assertFalse(self.evaluate([document])[0].eligible)

    def test_unknown_status_access_and_version_state(self):
        for field in ("status", "access_level", "version_state"):
            for value in ("unknown", [], None, True):
                document = copy.deepcopy(self.documents[0])
                document[field] = value
                with self.subTest(field=field, value=value):
                    self.assertFalse(validate_document(document).eligible)

    def test_malformed_metadata(self):
        cases = [("document_id", True), ("document_id", 0), ("title", " "),
                 ("version", ""), ("fictional", False), ("institution", "Other"),
                 ("effective_date", "2026-02-30"), ("effective_date", "20261025"),
                 ("source_reference", "https://example.invalid"), ("supersedes", True),
                 ("supersedes", 101), ("pages", []), ("pages", "text"),
                 ("pages", [{"page_no": True, "text": "fictional"}]),
                 ("pages", [{"page_no": 1, "text": " "}]),
                 ("pages", [{"page_no": 2, "text": "fictional"}])]
        for field, value in cases:
            document = copy.deepcopy(self.documents[0])
            document[field] = value
            with self.subTest(field=field, value=value):
                self.assertFalse(validate_document(document).eligible)
        for document in (None, [], "text", 12):
            self.assertFalse(validate_document(document).eligible)

    def test_unknown_fields_do_not_grant_permissions(self):
        self.documents[4]["trusted_permissions"] = ["staff"]
        self.assertTrue(all(not d.eligible for d in self.evaluate()))

    def test_rejection_does_not_expose_restricted_content(self):
        decision = self.evaluate()[4]
        self.assertEqual(asdict(decision), {"eligible": False, "reason": "access_denied"})
        result = repr(self.process())
        self.assertNotIn(self.documents[4]["title"], result)
        self.assertNotIn(self.documents[4]["pages"][0]["text"], result)
        self.assertNotIn(self.documents[4]["source_reference"], result)

    def test_multiple_pages_preserve_metadata_and_offsets(self):
        chunks = self.process(max_chars=45).chunks
        by_id = {d["document_id"]: d for d in self.documents}
        self.assertEqual({c.page_no for c in chunks if c.document_id == 101}, {1, 2})
        for chunk in chunks:
            document = by_id[chunk.document_id]
            for field in ("title", "version", "source_reference"):
                self.assertEqual(getattr(chunk, field), document[field])
            normalized = normalize_document_text(document["pages"][chunk.page_no - 1]["text"])
            self.assertEqual(chunk.chunk_text, normalized[chunk.start_char:chunk.end_char])

    def test_only_eligible_pages_reach_real_chunker(self):
        with patch("ai.document_eligibility.split_document_text", wraps=split_document_text) as chunker:
            result = self.process()
        self.assertEqual(chunker.call_count, 3)
        self.assertEqual({call.kwargs["document_id"] for call in chunker.call_args_list}, {101, 103})
        self.assertEqual({chunk.document_id for chunk in result.chunks}, {101, 103})
        self.assertEqual([call.args[0] for call in chunker.call_args_list],
                         [p["text"] for d in (self.documents[0], self.documents[2]) for p in d["pages"]])

    def test_deterministic_and_does_not_mutate_inputs(self):
        before = copy.deepcopy(self.documents)
        self.assertEqual(self.process(), self.process())
        self.assertEqual(self.documents, before)

    def test_historical_and_unknown_modes_fail_safely(self):
        for mode in ("historical", "unknown", None):
            with patch("ai.document_eligibility.split_document_text") as chunker:
                result = self.process(query_mode=mode)
                self.assertEqual(result.chunks, ())
                self.assertTrue(all(d.reason == "unsupported_query_mode" for d in result.decisions))
                chunker.assert_not_called()

    def test_invalid_reference_date(self):
        for value in (None, "2026-10-25", datetime(2026, 10, 25), True):
            self.assertTrue(all(d.reason == "invalid_reference_date"
                                for d in self.evaluate(reference_date=value)))

    def test_invalid_catalog_prevents_partial_processing(self):
        self.documents[-1]["pages"] = [{"page_no": 1, "text": None}]
        with patch("ai.document_eligibility.split_document_text") as chunker:
            self.assertEqual(self.process().chunks, ())
            chunker.assert_not_called()

    def test_duplicate_ids_missing_links_and_cycles(self):
        for case in ("duplicate", "missing", "cycle", "backwards_date"):
            documents = copy.deepcopy(self.documents)
            if case == "duplicate":
                documents.append(copy.deepcopy(documents[0]))
            elif case == "missing":
                documents[0]["supersedes"] = 999
            elif case == "cycle":
                documents[1]["supersedes"] = 101
                documents[1]["effective_date"] = documents[0]["effective_date"]
            else:
                documents[1]["effective_date"] = "2027-01-01"
            with self.subTest(case=case):
                self.assertTrue(all(d.reason == "invalid_catalog" for d in self.evaluate(documents)))

    def test_unavailable_replacement_never_revives_predecessor(self):
        for field, value in (("status", "draft"), ("status", "revoked"),
                             ("effective_date", "2027-01-01"), ("access_level", "staff")):
            documents = copy.deepcopy(self.documents)
            documents[0][field] = value
            documents[1]["version_state"] = "current"
            self.assertEqual(self.evaluate(documents)[1].reason, "superseded")

    def test_empty_and_nonlist_catalog(self):
        self.assertEqual(self.evaluate([]), ())
        for value in ({}, "text", 1):
            self.assertEqual(self.evaluate(value)[0].reason, "invalid_catalog")

    def test_loader_sanitizes_invalid_json_and_io_errors(self):
        for raw in ('{"status":"draft","status":"approved"}', '{bad', '{}'):
            with patch.object(Path, "read_text", return_value=raw):
                with self.assertRaisesRegex(ValueError, '^invalid_fixture$'):
                    load_fictional_documents(FIXTURE)
        with patch.object(Path, "read_text", side_effect=OSError("private path")):
            with self.assertRaisesRegex(ValueError, '^invalid_fixture$'):
                load_fictional_documents(FIXTURE)

    def test_invalid_chunk_limit_never_calls_chunker(self):
        for value in (True, 0, -1, "10"):
            with patch("ai.document_eligibility.split_document_text") as chunker:
                with self.assertRaisesRegex(ValueError, '^invalid_chunk_limit$'):
                    self.process(max_chars=value)
                chunker.assert_not_called()


if __name__ == "__main__":
    unittest.main()
