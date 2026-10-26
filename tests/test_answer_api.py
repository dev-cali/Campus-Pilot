"""Offline API and backend-output checks. No live model or production DB."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from ai.answer_service import AnswerService, validate_selection
from ai.demo_api import create_app
from ai.demo_store import DEFAULT_FIXTURE, DemoStore
from ai.document_eligibility import load_fictional_documents
from ai.local_retrieval import KeywordRetriever


REFERENCE_DATE = date(2026, 10, 26)


class AnswerApiTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = DemoStore(Path(directory.name) / "answers.sqlite3")
        self.addCleanup(self.store.close)
        self.store.initialize()
        self.documents = load_fictional_documents(DEFAULT_FIXTURE)
        self.store.seed(self.documents, reference_date=REFERENCE_DATE)
        self.retriever = KeywordRetriever(self.store)
        self.generator = Mock()
        self.service = AnswerService(self.retriever, self.generator)
        self.client = TestClient(create_app(self.service, reference_date=REFERENCE_DATE))
        self.addCleanup(self.client.close)

    def test_evaluation_cases_through_api(self):
        path = Path(__file__).parent / "fixtures" / "ai_eval_cases.json"
        cases = json.loads(path.read_text(encoding="utf-8"))["cases"]
        self.assertEqual(len(cases), 14)
        for case in cases:
            with self.subTest(case=case["id"]):
                self.generator.reset_mock(side_effect=True, return_value=True)

                def generate(_question, evidence):
                    mode = case["mode"]
                    if mode == "must_not_call":
                        raise AssertionError("Provider should not be called")
                    if mode == "timeout":
                        raise TimeoutError("private provider detail")
                    if mode == "provider_error":
                        raise RuntimeError("private provider detail")
                    if mode == "malformed":
                        return "not JSON: private provider detail"
                    if mode == "insufficient":
                        return json.dumps({"status": "insufficient_evidence", "selections": []})
                    chosen = next((item for item in evidence if case.get("quote", "") in item.chunk.chunk_text), evidence[0])
                    return json.dumps({"status": "answered", "selections": [{
                        "evidence_id": "invented" if mode == "invented_id" else chosen.evidence_id,
                        "quote": "Every student receives a fictional million coins." if mode == "invented_quote"
                                 else case.get("quote", chosen.chunk.chunk_text),
                    }]})

                self.generator.generate.side_effect = generate
                response = self.client.post("/api/ai/ask", json={"question": case["question"]})
                body = response.json()
                self.assertEqual(body["status"], case["expected_status"])
                self.assertEqual(response.status_code, {"unavailable": 503, "denied": 403}.get(body["status"], 200))
                self.assertEqual([c["document_id"] for c in body["citations"]], case["expected_ids"])
                self.assertTrue(body["fictional"])
                self.assertNotIn("private provider detail", response.text)
                self.assertNotIn("million coins", response.text)
                if case["mode"] == "must_not_call":
                    self.generator.generate.assert_not_called()
                else:
                    self.generator.generate.assert_called_once()
                    passed_evidence = self.generator.generate.call_args.args[1]
                    self.assertTrue(all(e.chunk.document_id in {101, 103} for e in passed_evidence))
                if body["status"] == "answered":
                    self.assertIn(case["quote"], body["answer"])
                    self.assertTrue(all(c["source_reference"].startswith("fictional://demo-campus/") for c in body["citations"]))

    def test_invalid_requests_do_not_call_model_or_echo_input(self):
        for payload in ({}, {"question": " "}, {"question": 123}, {"question": True},
                        {"question": "a" * 2001}, {"question": "scholarship", "is_staff": True}):
            response = self.client.post("/api/ai/ask", json=payload)
            self.assertEqual(response.status_code, 422)
            self.assertEqual(response.json(), {"detail": "Invalid question request."})
        response = self.client.post("/api/ai/ask", content="{bad", headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)
        self.generator.generate.assert_not_called()

    def test_invalid_output_variants_are_blocked(self):
        evidence = self.retriever.retrieve("scholarship", reference_date=REFERENCE_DATE)
        valid = {"evidence_id": evidence[0].evidence_id, "quote": evidence[0].chunk.chunk_text}
        variants = [
            {"status": "answered", "selections": []},
            {"status": "answered", "selections": [valid, valid]},
            {"status": "answered", "selections": [{"evidence_id": "e1", "quote": " "}]},
            {"status": "answered", "selections": [valid], "source_url": "invented"},
            {"status": "insufficient_evidence", "selections": [valid]},
            {"status": "unknown", "selections": []},
        ]
        for raw in [json.dumps(v) for v in variants] + ['{"status":"answered","status":"insufficient_evidence","selections":[]}', "x" * 20001]:
            self.generator.generate.return_value = raw
            answer = self.service.ask("scholarship", reference_date=REFERENCE_DATE)
            self.assertEqual(answer.status, "unavailable")
            self.assertEqual(answer.citations, [])

    def test_sources_revoked_during_generation_block_answer(self):
        def revoke(_question, evidence):
            self.documents[0]["status"] = "revoked"
            self.store.seed(self.documents, reference_date=REFERENCE_DATE)
            return json.dumps({"status": "answered", "selections": [{
                "evidence_id": evidence[0].evidence_id, "quote": evidence[0].chunk.chunk_text,
            }]})
        self.generator.generate.side_effect = revoke
        answer = self.service.ask("scholarship", reference_date=REFERENCE_DATE)
        self.assertEqual(answer.status, "unavailable")
        self.assertEqual(answer.citations, [])

    def test_storage_failure_returns_neutral_unavailable(self):
        source = Mock()
        source.retrieve.side_effect = RuntimeError("private database detail")
        answer = AnswerService(source, self.generator).ask("enrollment", reference_date=REFERENCE_DATE)
        self.assertEqual(answer.status, "unavailable")
        self.assertNotIn("private database detail", answer.model_dump_json())
        self.generator.generate.assert_not_called()

    def test_quote_check_is_not_semantic_answer_verification(self):
        # Explicit limitation test: a real excerpt can still fail to answer a
        # question. This validator has no question input and cannot prove that.
        evidence = self.retriever.retrieve("scholarship", reference_date=REFERENCE_DATE)
        raw = json.dumps({"status": "answered", "selections": [{
            "evidence_id": evidence[0].evidence_id, "quote": "FICTIONAL TEST DATA.",
        }]})
        self.assertEqual(validate_selection(raw, evidence).status, "answered")


if __name__ == "__main__":
    unittest.main()
