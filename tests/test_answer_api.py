"""Offline API and backend-output checks. No live model or production DB."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock

from fastapi.testclient import TestClient

from ai.answer_service import AnswerService, IncompleteAnswer, _answer_question_parts, validate_selection
from ai.demo_api import create_app
from ai.demo_store import DEFAULT_FIXTURE, DemoStore
from ai.document_eligibility import load_fictional_documents
from ai.local_retrieval import Evidence, KeywordRetriever


REFERENCE_DATE = date(2026, 10, 26)


def supported_part(question, evidence, answer_text, quotes=None, *, index=0, part_text=None):
    selected_quotes = quotes or [(evidence[0], evidence[0].chunk.chunk_text[:180])]
    return {
        "part_index": index + 1,
        "part_text": part_text or _answer_question_parts(question)[index],
        "support": "supported",
        "answer_text": answer_text,
        "evidence": [{"evidence_id": item.evidence_id, "quote": quote}
                     for item, quote in selected_quotes],
    }


class AnswerApiTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.store = DemoStore(Path(directory.name) / "answers.sqlite3")
        self.addCleanup(self.store.close)
        self.store.initialize()
        all_documents = load_fictional_documents(DEFAULT_FIXTURE)
        # Keep the pre-expansion API/evaluation regression corpus isolated.
        self.documents = [d for d in all_documents if d["document_id"] <= 106]
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
                    quote = ("Every student receives a fictional million coins." if mode == "invented_quote"
                             else case.get("quote", chosen.chunk.chunk_text))
                    return json.dumps({"status": "answered", "parts": [{
                        "part_index": 1,
                        "part_text": _answer_question_parts(_question)[0],
                        "support": "supported",
                        "answer_text": ("Every student receives a fictional million coins."
                                        if mode == "invented_quote" else
                                        "The scholarship practice form is imaginary."
                                        if "practice form" in _question else
                                        "Learners review a sample course list in this exercise."),
                        "evidence": [{
                            "evidence_id": "invented" if mode == "invented_id" else chosen.evidence_id,
                            "quote": quote,
                        }],
                    }]})

                self.generator.generate.side_effect = generate
                response = self.client.post("/api/ai/ask", json={"question": case["question"]})
                body = response.json()
                # Unsupported injection requests can now stop before the mock
                # provider runs. Malformed output with retrieved evidence is
                # still covered by the output-validation cases below.
                no_evidence_injection = (
                    case["mode"] == "invented_quote"
                    and not self.retriever.retrieve(case["question"], reference_date=REFERENCE_DATE)
                )
                expected_status = (
                    "insufficient_evidence" if no_evidence_injection else case["expected_status"]
                )
                self.assertEqual(body["status"], expected_status)
                self.assertEqual(response.status_code, {"unavailable": 503, "denied": 403}.get(body["status"], 200))
                self.assertEqual([c["document_id"] for c in body["citations"]], case["expected_ids"])
                self.assertTrue(body["fictional"])
                self.assertNotIn("private provider detail", response.text)
                self.assertNotIn("million coins", response.text)
                if case["mode"] == "must_not_call" or no_evidence_injection:
                    self.generator.generate.assert_not_called()
                else:
                    self.generator.generate.assert_called_once()
                    passed_evidence = self.generator.generate.call_args.args[1]
                    self.assertTrue(all(e.chunk.document_id in {101, 103} for e in passed_evidence))
                if body["status"] == "answered":
                    self.assertIn("Based on fictional", body["answer"])
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
                            {"part_index": 1, "part_text": _answer_question_parts(_question)[0],
                             "support": "supported", "answer_text": "Learners review a sample course list in this exercise.",
                             "evidence": [{"evidence_id": selected.evidence_id,
                                           "quote": evaluation["supported_quote"]}]},
                            {"part_index": 2, "part_text": _answer_question_parts(_question)[1],
                             "support": "unsupported", "answer_text": None, "evidence": []}]})
                    if scenario["mock_behavior"] == "quotes_supported_part_only":
                        return json.dumps({"status": "answered", "parts": [{
                            "part_index": 1, "part_text": _answer_question_parts(_question)[0],
                            "support": "supported",
                            "answer_text": "Learners review a sample course list in this exercise.",
                            "evidence": [{"evidence_id": selected.evidence_id,
                                          "quote": evaluation["supported_quote"]}],
                        }]})
                    raise AssertionError("Unknown partial-support mock behavior")

                self.generator.generate.side_effect = generate
                response = self.client.post("/api/ai/ask", json={"question": evaluation["question"]})
                body = response.json()
                self.assertEqual(response.status_code, 200)
                self.assertEqual(body["status"], evaluation["desired_status"])
                self.generator.generate.assert_called_once()
                passed_evidence = self.generator.generate.call_args.args[1]
                self.assertTrue(any(
                    item.chunk.document_id == evaluation["supported_document_id"]
                    and evaluation["supported_quote"] in item.chunk.chunk_text
                    for item in passed_evidence
                ))

                self.assertEqual(body["citations"], [])

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
        question_parts = _answer_question_parts(question)
        for index, (document_id, quote) in enumerate(expected, 1):
            source = next(item for item in evidence
                          if item.chunk.document_id == document_id and quote in item.chunk.chunk_text)
            sources.append(source)
            answer_text = ("Learners review a sample course list in this exercise."
                           if document_id == 103
                           else "The scholarship practice form is imaginary.")
            parts.append({"part_index": index, "part_text": question_parts[index - 1],
                          "support": "supported", "answer_text": answer_text,
                          "evidence": [{"evidence_id": source.evidence_id, "quote": quote}]})
        self.generator.generate.return_value = json.dumps({"status": "answered", "parts": parts})
        response = self.client.post("/api/ai/ask", json={"question": question})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "answered")
        self.assertEqual([c["document_id"] for c in body["citations"]], [103, 101])
        for source, (_, quote), citation in zip(sources, expected, body["citations"]):
            self.assertIn(quote, source.chunk.chunk_text)
            self.assertEqual(citation["evidence_id"], source.evidence_id)
            for field in ("title", "page_no", "version", "source_reference"):
                self.assertEqual(citation[field], getattr(source.chunk, field))
        self.generator.generate.assert_called_once()
        self.assertTrue(body["fictional"])
        self.assertEqual(set(body), {"status", "answer", "citations", "fictional"})

    def test_generic_marker_quote_is_rejected_as_irrelevant(self):
        question = (
            "What do fictional learners review for enrollment, and what does the "
            "scholarship practice form represent?"
        )
        evidence = self.retriever.retrieve(question, reference_date=REFERENCE_DATE)
        self.assertEqual(len(evidence), 2)
        parts = [
            {"part_index": 1, "part_text": _answer_question_parts(question)[0],
             "support": "supported", "answer_text": "Learners review the course list for enrollment.",
             "evidence": [{"evidence_id": evidence[0].evidence_id,
                           "quote": "FICTIONAL TEST DATA."}]},
            {"part_index": 2, "part_text": _answer_question_parts(question)[1],
             "support": "supported", "answer_text": "The scholarship practice form is fictional.",
             "evidence": [{"evidence_id": evidence[1].evidence_id,
                           "quote": "FICTIONAL TEST DATA."}]},
        ]
        self.generator.generate.return_value = json.dumps({"status": "answered", "parts": parts})
        response = self.client.post("/api/ai/ask", json={"question": question})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "insufficient_evidence")
        self.assertEqual(response.json()["citations"], [])
        self.assertEqual(set(response.json()), {"status", "answer", "citations", "fictional"})

    def test_question_part_coverage_and_shared_citation(self):
        from ai.document_processing import split_document_text
        question = "When does enrollment open, and when is orientation?"
        chunk = split_document_text(
            "FICTIONAL TEST DATA. Enrollment opens January 4, 2027. Orientation is January 9, 2027.",
            document_id=1, page_no=1, source_reference="fictional://demo-campus/1/v1",
            title="Fictional calendar", version="v1",
        )[0]
        evidence = (Evidence("e1", chunk, ()),)
        parts = [
            {"part_index": 1, "part_text": _answer_question_parts(question)[0],
             "support": "supported", "answer_text": "Enrollment opens January 4, 2027.",
             "evidence": [{"evidence_id": "e1", "quote": "Enrollment opens January 4, 2027."}]},
            {"part_index": 2, "part_text": _answer_question_parts(question)[1],
             "support": "supported", "answer_text": "Orientation is January 9, 2027.",
             "evidence": [{"evidence_id": "e1", "quote": "Orientation is January 9, 2027."}]},
        ]
        response = validate_selection(json.dumps({"status": "answered", "parts": parts}), evidence, question)
        self.assertEqual(response.status, "answered")
        self.assertIn("January 4, 2027", response.answer)
        self.assertIn("January 9, 2027", response.answer)
        self.assertEqual(len(response.citations), 1)

    def test_malformed_coverage_fails_safely(self):
        question = "scholarship practice form"
        evidence = self.retriever.retrieve(question, reference_date=REFERENCE_DATE)
        valid = {"part_index": 1, "part_text": question, "support": "supported",
                 "answer_text": "The scholarship practice form is imaginary.",
                 "evidence": [{"evidence_id": evidence[0].evidence_id,
                               "quote": evidence[0].chunk.chunk_text[:180]}]}
        mutations = [dict(valid, **change) for change in (
            {"part_index": 0}, {"part_index": 2}, {"part_index": True},
            {"part_index": "1"}, {"part_text": ""}, {"part_text": "invented"},
            {"support": "maybe"}, {"answer_text": None}, {"answer_text": ""},
            {"evidence": []}, {"evidence": [{"evidence_id": "invented", "quote": "scholarship practice form"}]},
            {"evidence": [{"evidence_id": evidence[0].evidence_id, "quote": "invented"}]},
            {"evidence": [{"evidence_id": evidence[0].evidence_id, "quote": " "}]},
            {"evidence": [{"evidence_id": evidence[0].evidence_id, "quote": "x" * 181}]},
            {"evidence": [{"evidence_id": evidence[0].evidence_id, "quote": valid["evidence"][0]["quote"], "extra": "x"}]},
            {"extra": "untrusted"})]
        mutations += [{k: v for k, v in valid.items() if k != missing} for missing in valid]
        variants = [{"status": "answered", "parts": [part]} for part in mutations]
        variants += [
            {"status": "unknown", "parts": []},
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
                           "support": "unsupported", "answer_text": None, "evidence": []}]):
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
                "part_index": 1, "part_text": _answer_question_parts(_question)[0],
                "support": "supported", "answer_text": "The scholarship practice form is imaginary.",
                "evidence": [{"evidence_id": evidence[0].evidence_id,
                              "quote": evidence[0].chunk.chunk_text[:180]}],
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

    def test_generic_marker_quote_is_not_valid_semantic_support(self):
        evidence = self.retriever.retrieve("scholarship", reference_date=REFERENCE_DATE)
        raw = json.dumps({"status": "answered", "parts": [{
            "part_index": 1, "part_text": "scholarship", "support": "supported",
            "answer_text": "The scholarship is available.",
            "evidence": [{"evidence_id": evidence[0].evidence_id,
                          "quote": "FICTIONAL TEST DATA."}],
        }]})
        with self.assertRaises(IncompleteAnswer):
            validate_selection(raw, evidence, "scholarship")


if __name__ == "__main__":
    unittest.main()
