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
        self.client = TestClient(
    create_app(
        self.service,
        reference_date=REFERENCE_DATE,
        require_auth=False,
    )
)
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
                        return json.dumps({"status": "insufficient_evidence", "parts": []})
                    chosen = next((item for item in evidence if case.get("quote", "") in item.chunk.chunk_text), evidence[0])
                    return json.dumps({"status": "answered", "parts": [{
                        "part_index": 1, "part_text": _question, "support": "supported",
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

    def test_partial_support_evaluation_records_desired_and_observed_behavior(self):
        path = Path(__file__).parent / "fixtures" / "ai_eval_cases.json"
        evaluation = json.loads(path.read_text(encoding="utf-8"))["partial_support_evaluation"]
        self.assertEqual(evaluation["desired_status"], "insufficient_evidence")
        self.assertEqual(len(evaluation["scenarios"]), 2)

        for scenario in evaluation["scenarios"]:
            with self.subTest(scenario=scenario["id"]):
                self.generator.reset_mock(side_effect=True, return_value=True)

                def generate(_question, evidence):
                    selected = next(
                        item for item in evidence
                        if item.chunk.document_id == evaluation["supported_document_id"]
                        and evaluation["supported_quote"] in item.chunk.chunk_text
                    )
                    if scenario["mock_behavior"] == "cooperative_abstention":
                        return json.dumps({"status": "insufficient_evidence", "parts": [
                            {"part_index": 1, "part_text": _question.split(", and ")[0],
                             "support": "supported", "evidence_id": selected.evidence_id,
                             "quote": evaluation["supported_quote"]},
                            {"part_index": 2, "part_text": _question.split(", and ")[1],
                             "support": "unsupported", "evidence_id": None, "quote": None}]})
                    if scenario["mock_behavior"] == "quotes_supported_part_only":
                        return json.dumps({"status": "answered", "parts": [{
                            "part_index": 1, "part_text": _question.split(", and ")[0], "support": "supported",
                            "evidence_id": selected.evidence_id,
                            "quote": evaluation["supported_quote"],
                        }]})
                    raise AssertionError("Unknown partial-support mock behavior")

                self.generator.generate.side_effect = generate
                response = self.client.post("/api/ai/ask", json={"question": evaluation["question"]})
                body = response.json()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(body["status"], scenario["observed_status"])
                self.generator.generate.assert_called_once()
                passed_evidence = self.generator.generate.call_args.args[1]
                self.assertTrue(any(
                    item.chunk.document_id == evaluation["supported_document_id"]
                    and evaluation["supported_quote"] in item.chunk.chunk_text
                    for item in passed_evidence
                ))

                if scenario["mock_behavior"] == "cooperative_abstention":
                    self.assertEqual(body["status"], evaluation["desired_status"])
                    self.assertEqual(body["citations"], [])
                else:
                    # This passing assertion records the known gap: a genuine
                    # model can omit a request; declared coverage cannot detect omission.
                    self.assertNotEqual(body["status"], evaluation["desired_status"])
                    self.assertIn(evaluation["supported_quote"], body["answer"])
                    self.assertEqual(
                        [citation["document_id"] for citation in body["citations"]],
                        [evaluation["supported_document_id"]],
                    )

    def test_natural_two_part_answer_uses_relevant_fictional_passages(self):
        requests = ["What do imaginary learners review for enrollment",
                    "which scholarship form is used"]
        question = requests[0] + ", and " + requests[1] + "?"
        expected = [
            (103, "Demo Campus University asks imaginary learners to review a sample course list in this exercise."),
            (101, "Demo Campus University uses an imaginary scholarship practice form."),
        ]
        evidence = self.retriever.retrieve(question, reference_date=REFERENCE_DATE)
        parts, sources = [], []
        for index, (document_id, quote) in enumerate(expected, 1):
            source = next(item for item in evidence
                          if item.chunk.document_id == document_id and quote in item.chunk.chunk_text)
            sources.append(source)
            parts.append({"part_index": index, "part_text": requests[index - 1],
                          "support": "supported", "evidence_id": source.evidence_id, "quote": quote})
        self.generator.generate.return_value = json.dumps({"status": "answered", "parts": parts})
        response = self.client.post("/api/ai/ask", json={"question": question})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "answered")
        self.assertEqual([c["document_id"] for c in body["citations"]], [103, 101])
        for source, (_, quote), citation in zip(sources, expected, body["citations"]):
            self.assertIn(quote, body["answer"])
            self.assertEqual(citation["evidence_id"], source.evidence_id)
            for field in ("title", "page_no", "version", "source_reference"):
                self.assertEqual(citation[field], getattr(source.chunk, field))
        self.generator.generate.assert_called_once()
        self.assertTrue(body["fictional"])
        self.assertEqual(set(body), {"status", "answer", "citations", "fictional"})

    def test_structural_shared_citations_do_not_establish_relevance(self):
        # Generic markers exercise structure/deduplication only, not answer quality.
        question = "scholarship enrollment"
        evidence = self.retriever.retrieve(question, reference_date=REFERENCE_DATE)
        self.assertEqual(len(evidence), 2)
        def part(index, text, item):
            return {"part_index": index, "part_text": text, "support": "supported",
                    "evidence_id": item.evidence_id, "quote": "FICTIONAL TEST DATA."}
        for shared in (False, True):
            with self.subTest(shared=shared):
                parts = [part(1, "scholarship", evidence[0]),
                         part(2, "enrollment", evidence[0 if shared else 1])]
                self.generator.generate.return_value = json.dumps({"status": "answered", "parts": parts})
                response = self.client.post("/api/ai/ask", json={"question": question})
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["status"], "answered")
                self.assertEqual(len(body["citations"]), 1 if shared else 2)
                self.assertEqual(body["citations"][0]["title"], evidence[0].chunk.title)
                self.assertEqual(body["answer"].count("FICTIONAL TEST DATA."), 2)
                self.assertEqual(set(body), {"status", "answer", "citations", "fictional"})

    def test_malformed_coverage_fails_safely(self):
        question = "scholarship enrollment"
        evidence = self.retriever.retrieve(question, reference_date=REFERENCE_DATE)
        valid = {"part_index": 1, "part_text": "scholarship", "support": "supported",
                 "evidence_id": evidence[0].evidence_id, "quote": "FICTIONAL TEST DATA."}
        mutations = [dict(valid, **change) for change in (
            {"part_index": 0}, {"part_index": 2}, {"part_index": True},
            {"part_index": "1"}, {"part_text": ""}, {"part_text": " "},
            {"part_text": "invented"}, {"support": "maybe"},
            {"evidence_id": None}, {"evidence_id": "invented"}, {"quote": None},
            {"quote": "invented"}, {"quote": " "}, {"quote": "x" * 301},
            {"support": "unsupported"}, {"extra": "untrusted"})]
        mutations += [{k: v for k, v in valid.items() if k != missing} for missing in valid]
        variants = [{"status": "answered", "parts": [part]} for part in mutations]
        unsupported = dict(valid, support="unsupported", evidence_id=None, quote=None)
        variants += [
            {"status": "answered", "parts": [unsupported]},
            {"status": "insufficient_evidence", "parts": [valid]},
            {"status": "answered", "parts": [valid, dict(valid, part_index=2)]},
            {"status": "answered", "parts": [valid, valid, valid]},
            {"status": "insufficient_evidence", "parts": [unsupported, dict(valid, part_index=2, part_text="enrollment", quote="invented")]},
        ]
        for output in variants:
            with self.subTest(output=output):
                self.generator.generate.return_value = json.dumps(output)
                response = self.client.post("/api/ai/ask", json={"question": question})
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()["status"], "unavailable")
                self.assertEqual(response.json()["citations"], [])

    def test_overflow_and_all_unsupported_abstain(self):
        question = "scholarship and enrollment and library hours"
        for parts in ([], [{"part_index": 1, "part_text": question,
                           "support": "unsupported", "evidence_id": None, "quote": None}]):
            self.generator.generate.return_value = json.dumps({"status": "insufficient_evidence", "parts": parts})
            response = self.client.post("/api/ai/ask", json={"question": question})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "insufficient_evidence")
            self.assertEqual(response.json()["citations"], [])

    def test_actual_mock_demo_api_offline(self):
        import runpy
        namespace = runpy.run_path(str(Path(__file__).parent / "frontend_demo_server.py"))
        service = namespace["LabeledMockService"](self.retriever, namespace["MockGenerator"]())
        with TestClient(
    create_app(
        service,
        reference_date=REFERENCE_DATE,
        require_auth=False,
    )
) as client:
            for question, status in (
                ("What sample course list do fictional learners review for enrollment?", "answered"),
                ("What do fictional learners review for enrollment?", "answered"),
                ("What is the scholarship GPA requirement?", "insufficient_evidence"),
                ("Explain scholarship enrollment library hours.", "insufficient_evidence")):
                response = client.post("/api/ai/ask", json={"question": question})
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["status"], status)
                self.assertTrue(body["answer"].startswith("[MOCK DEMONSTRATION \u2014 no LLM call]"))
                self.assertTrue(body["fictional"])
                if status == "answered":
                    self.assertEqual(len(body["citations"]), 1)
                    citation = body["citations"][0]
                    self.assertEqual(citation["document_id"], 103)
                    source = self.retriever.retrieve(question, reference_date=REFERENCE_DATE)[0].chunk
                    self.assertEqual(citation["source_reference"], source.source_reference)
                    self.assertEqual(citation["title"], source.title)
                    self.assertEqual(citation["version"], source.version)
                else:
                    self.assertEqual(body["citations"], [])

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
        valid = {"part_index": 1, "part_text": "scholarship", "support": "supported", "evidence_id": evidence[0].evidence_id, "quote": evidence[0].chunk.chunk_text}
        variants = [
            {"status": "answered", "parts": []},
            {"status": "answered", "parts": [valid, valid]},
            {"status": "answered", "parts": [{"evidence_id": "e1", "quote": " "}]},
            {"status": "answered", "parts": [valid], "source_url": "invented"},
            {"status": "insufficient_evidence", "parts": [valid]},
            {"status": "unknown", "parts": []},
        ]
        for raw in [json.dumps(v) for v in variants] + ['{"status":"answered","status":"insufficient_evidence","parts":[]}', "x" * 20001]:
            self.generator.generate.return_value = raw
            answer = self.service.ask("scholarship", reference_date=REFERENCE_DATE)
            self.assertEqual(answer.status, "unavailable")
            self.assertEqual(answer.citations, [])

    def test_sources_revoked_during_generation_block_answer(self):
        def revoke(_question, evidence):
            self.documents[0]["status"] = "revoked"
            self.store.seed(self.documents, reference_date=REFERENCE_DATE)
            return json.dumps({"status": "answered", "parts": [{
                "part_index": 1, "part_text": _question, "support": "supported",
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
        # question. Exact membership still cannot prove semantic relevance.
        evidence = self.retriever.retrieve("scholarship", reference_date=REFERENCE_DATE)
        raw = json.dumps({"status": "answered", "parts": [{
            "part_index": 1, "part_text": "scholarship", "support": "supported",
            "evidence_id": evidence[0].evidence_id, "quote": "FICTIONAL TEST DATA.",
        }]})
        self.assertEqual(validate_selection(raw, evidence, "scholarship").status, "answered")


if __name__ == "__main__":
    unittest.main()
