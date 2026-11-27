"""Offline Phase 5 answer grounding and calculation tests; no live model calls."""

import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock

from ai.answer_service import AnswerService, IncompleteAnswer, _answer_question_parts, validate_selection
from ai.demo_store import DemoStore
from ai.document_eligibility import load_fictional_documents
from ai.document_processing import split_document_text
from ai.local_retrieval import Evidence, KeywordRetriever
from answer_quality_evaluation import evaluate_answer_quality


REFERENCE_DATE = date(2026, 11, 27)


class FixedRetriever:
    def __init__(self, evidence):
        self.evidence = evidence

    def retrieve(self, _question, *, reference_date):
        return self.evidence


class AnswerQualityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="campuspilot-answer-quality-")
        self.addCleanup(self.temp.cleanup)
        self.store = DemoStore(Path(self.temp.name) / "answer-quality.sqlite3")
        self.addCleanup(self.store.close)
        self.store.initialize()
        docs = load_fictional_documents(Path(__file__).parent / "fixtures" / "fictional_documents.json")
        self.store.seed(docs, reference_date=REFERENCE_DATE)
        self.chunks = self.store.public_chunks(reference_date=REFERENCE_DATE)
        self.generator = Mock()

    def test_phase5_dataset_has_40_source_located_cases_and_handoff_targets(self):
        fixture = json.loads((Path(__file__).parent / "fixtures" / "answer_quality_phase5.json").read_text(
            encoding="utf-8"))
        cases = fixture["cases"]
        self.assertEqual(len(cases), 40)
        self.assertEqual(sum(bool(case.get("phase4_4_handoff_target")) for case in cases), 11)
        self.assertEqual(len({case["id"] for case in cases}), 40)
        locators = {(chunk.document_id, chunk.page_no) for chunk in self.chunks}
        for case in cases:
            with self.subTest(case=case["id"]):
                for group in case["required_evidence_groups"]:
                    self.assertTrue(group)
                    for locator in group:
                        self.assertIn((locator["document_id"], locator["page_no"]), locators)
                if case["expected_status"] == "answered" and not case.get("calculation"):
                    self.assertEqual(len(case["answer_texts"]),
                                     len(_answer_question_parts(case["question"])))

    def test_layer_a_component_and_layer_b_real_retrieval_evaluation(self):
        result = evaluate_answer_quality()
        layer_a = result["layer_A_component"]
        layer_b = result["layer_B_end_to_end"]
        self.assertEqual(result["case_count"], 40)
        self.assertGreaterEqual(layer_a["supported_complete"] / layer_a["supported_total"], 0.90)
        self.assertEqual(layer_a["citation_failures"], 0)
        self.assertEqual(layer_b["incorrectly_accepted_unsupported"], 0)
        self.assertEqual(layer_b["citation_failures"], 0)
        self.assertTrue(all(not case["forbidden_claims_present"]
                            for case in layer_b["cases"]))
        self.assertIn("planned_not_executed", result["layer_C_live_model_plan"]["status"])
        self.assertGreaterEqual(layer_b["supported_complete_retrieval"]
                                + layer_b["supported_incomplete_retrieval"],
                                result["supported_case_count"])

    def evidence(self, *locators):
        selected = []
        for document_id, page_no in locators:
            chunk = next(c for c in self.chunks
                         if (c.document_id, c.page_no, c.chunk_index) == (document_id, page_no, 0))
            selected.append(Evidence(f"e{len(selected) + 1}", chunk, ()))
        return tuple(selected)

    def service(self, evidence):
        return AnswerService(FixedRetriever(evidence), self.generator)

    def test_deterministic_tuition_only_total_and_different_load(self):
        evidence = self.evidence((110, 1))
        cases = (
            ("How much is tuition for 18 units before scholarships, excluding fixed charges?", "₱18,000", "excluding fixed charges"),
            ("What is the total assessment for 18 units before scholarships?", "₱21,000", "₱3,000 fixed charges"),
            ("What is the total assessment for 15 units before scholarships?", "₱18,000", "₱15,000"),
        )
        for question, expected, supporting_text in cases:
            with self.subTest(question=question):
                self.generator.reset_mock()
                result = self.service(evidence).ask(question, reference_date=REFERENCE_DATE)
                self.assertEqual(result.status, "answered")
                self.assertIn(expected, result.answer)
                self.assertIn(supporting_text, result.answer)
                self.assertEqual([citation.document_id for citation in result.citations], [110])
                self.generator.generate.assert_not_called()

    def test_conditional_scholarship_discount_affects_tuition_only(self):
        evidence = self.evidence((110, 1), (109, 2))
        question = "If I receive the Lakbay 50% tuition award and take 18 units, what would my assessment be?"
        result = self.service(evidence).ask(question, reference_date=REFERENCE_DATE)
        self.assertEqual(result.status, "answered")
        self.assertIn("₱12,000", result.answer)
        self.assertIn("₱9,000", result.answer)
        self.assertIn("₱3,000 fixed charges", result.answer)
        self.assertIn("conditional, not award approval", result.answer)
        self.assertEqual({citation.document_id for citation in result.citations}, {109, 110})
        self.generator.generate.assert_not_called()

    def test_installments_are_calculated_from_verified_balance_and_schedule(self):
        evidence = self.evidence((110, 2))
        question = "For a verified ₱21,000 assessment under the 40/30/30 plan, what are the installments?"
        result = self.service(evidence).ask(question, reference_date=REFERENCE_DATE)
        self.assertEqual(result.status, "answered")
        for amount in ("₱8,400", "₱6,300", "₱6,300"):
            self.assertIn(amount, result.answer)
        self.assertEqual([citation.document_id for citation in result.citations], [110])
        self.generator.generate.assert_not_called()

    def test_fixed_charge_breakdown_and_total_are_parsed_from_evidence(self):
        evidence = self.evidence((110, 1))
        result = self.service(evidence).ask(
            "Which fixed academic charges are added to tuition?", reference_date=REFERENCE_DATE,
        )
        self.assertEqual(result.status, "answered")
        for label, amount in (("registration", "₱700"), ("library resources", "₱500"),
                              ("technology", "₱800"), ("student services", "₱1,000"),
                              ("total fixed charges", "₱3,000")):
            self.assertIn(label.casefold(), result.answer.casefold())
            self.assertIn(amount, result.answer)
        self.assertEqual([citation.document_id for citation in result.citations], [110])
        self.generator.generate.assert_not_called()

    def test_financial_calculations_abstain_when_operands_are_missing_or_invalid(self):
        partial_rate = split_document_text(
            "Fictional tuition is ₱1,000 per unit.", document_id=110, page_no=1,
            source_reference="fictional://demo-campus/110/v1", title="Fictional tuition", version="v1",
        )[0]
        rate_only = (Evidence("e1", partial_rate, ()),)
        cases = (
            ("How much tuition for an unspecified number of units?", rate_only),
            ("What is tuition for 18.5 units?", rate_only),
            ("What is tuition for -2 units?", rate_only),
            ("What is tuition for 1001 units?", rate_only),
            ("What is the total assessment for 18 units?", rate_only),
            ("If I receive a scholarship and take 18 units, what is my assessment?", rate_only),
        )
        for question, evidence in cases:
            with self.subTest(question=question):
                self.generator.reset_mock()
                result = self.service(evidence).ask(question, reference_date=REFERENCE_DATE)
                self.assertEqual(result.status, "insufficient_evidence")
                self.assertEqual(result.citations, [])
                self.generator.generate.assert_not_called()

    def test_conflicting_rates_and_unverified_installment_schedule_abstain(self):
        first = split_document_text("Fictional tuition is ₱1,000 per unit.", document_id=1,
            page_no=1, source_reference="fictional://demo-campus/1/v1", title="Rate one", version="v1")[0]
        second = split_document_text("Fictional tuition is ₱1,200 per unit.", document_id=2,
            page_no=1, source_reference="fictional://demo-campus/2/v1", title="Rate two", version="v1")[0]
        conflicting = (Evidence("e1", first, ()), Evidence("e2", second, ()))
        result = self.service(conflicting).ask(
            "What is the tuition total for 18 units?", reference_date=REFERENCE_DATE,
        )
        self.assertEqual(result.status, "insufficient_evidence")
        self.assertEqual(result.citations, [])
        no_schedule = self.evidence((110, 1))
        result = self.service(no_schedule).ask(
            "For a ₱21,000 assessment, how much are the installments?", reference_date=REFERENCE_DATE,
        )
        self.assertEqual(result.status, "insufficient_evidence")

    def test_unanchored_answer_claims_and_values_fail_closed(self):
        item = self.evidence((107, 1))[0]
        question = "When does Term A enrollment open?"
        base = {"part_index": 1, "part_text": _answer_question_parts(question)[0], "support": "supported",
                "answer_text": "Term A enrollment opens January 4, 2027.",
                "evidence": [{"evidence_id": item.evidence_id,
                              "quote": "Term A academic calendar. Enrollment opens January 4, 2027, and closes January 8, 2027."}]}
        valid = validate_selection(json.dumps({"status": "answered", "parts": [base]}),
                                   (item,), question)
        self.assertEqual(valid.status, "answered")
        mutations = (
            dict(base, answer_text="Enrollment opens February 9, 2030."),
            dict(base, answer_text="Enrollment opens January 4, 2027 and registration is guaranteed."),
            dict(base, answer_text="Orientation begins January 4, 2027."),
            dict(base, evidence=[{"evidence_id": "invented", "quote": base["evidence"][0]["quote"]}]),
            dict(base, evidence=[{"evidence_id": item.evidence_id, "quote": "The term closes May 14, 2027."}]),
        )
        for part in mutations:
            with self.subTest(part=part):
                output = json.dumps({"status": "answered", "parts": [part]})
                if part["evidence"][0]["evidence_id"] == "invented" or part["evidence"][0]["quote"] not in item.chunk.chunk_text:
                    with self.assertRaises(ValueError):
                        validate_selection(output, (item,), question)
                else:
                    with self.assertRaises(IncompleteAnswer):
                        validate_selection(output, (item,), question)

    def test_non_answered_statuses_carry_no_citations(self):
        answer = validate_selection(json.dumps({"status": "insufficient_evidence", "parts": []}),
                                    self.evidence((107, 1)), "unavailable question")
        self.assertEqual(answer.status, "insufficient_evidence")
        self.assertEqual(answer.citations, [])

    def test_adversarial_answers_omissions_procedures_approval_and_arithmetic_abstain(self):
        cases = (
            ("What GPA and unit load does Lakbay require, including whether failed courses are allowed?",
             ((109, 2),), "Lakbay GPA must not exceed 1.75 and requires at least 15 units.",
             "Lakbay Academic Merit Award: Term GPA must not exceed 1.75 on this scale; carry at least 15 units and have no failed courses."),
            ("Am I approved for the Lakbay scholarship?", ((109, 2),),
             "You are approved for the Lakbay scholarship.",
             "This example creates no actual award or entitlement."),
            ("How do I complete simulated enrollment?", ((111, 2),),
             "Pay the Dean before online submission.",
             "submit it to the Registrar, and receive simulated confirmation"),
            ("What is the total assessment for 18 units before scholarships?", ((110, 1),),
             "The total assessment is ₱20,000.",
             "18 units × ₱1,000 = ₱18,000 tuition; plus ₱3,000 fixed charges = ₱21,000 total"),
        )
        for question, locators, answer_text, quote_part in cases:
            with self.subTest(question=question):
                evidence = self.evidence(*locators)
                source = next(item for item in evidence if quote_part in item.chunk.chunk_text)
                part = {"part_index": 1, "part_text": _answer_question_parts(question)[0],
                        "support": "supported", "answer_text": answer_text,
                        "evidence": [{"evidence_id": source.evidence_id, "quote": quote_part}]}
                raw = json.dumps({"status": "answered", "parts": [part]})
                with self.assertRaises(IncompleteAnswer):
                    validate_selection(raw, evidence, question)

    def test_conflicting_monetary_quotes_are_not_accepted(self):
        from ai.document_processing import split_document_text

        first = self.evidence((110, 1))[0]
        other_chunk = split_document_text(
            "FICTIONAL TEST DATA. Tuition costs ₱1,200 per unit.", document_id=999, page_no=1,
            source_reference="fictional://demo-campus/999/v1", title="Conflict fixture", version="v1",
        )[0]
        second = Evidence("e2", other_chunk, ())
        question = "What is the tuition rate per unit?"
        quote1 = "Term A tuition is ₱1,000 per unit."
        quote2 = "Tuition costs ₱1,200 per unit."
        part = {"part_index": 1, "part_text": _answer_question_parts(question)[0], "support": "supported",
                "answer_text": "Tuition is ₱1,000 per unit.",
                "evidence": [{"evidence_id": first.evidence_id, "quote": quote1},
                             {"evidence_id": second.evidence_id, "quote": quote2}]}
        with self.assertRaises(IncompleteAnswer):
            validate_selection(json.dumps({"status": "answered", "parts": [part]}),
                               (first, second), question)

    def test_missing_duplicate_and_excessive_parts_fail_closed(self):
        evidence = self.evidence((107, 1))
        question = "When does enrollment open, and when is orientation?"
        first = {"part_index": 1, "part_text": _answer_question_parts(question)[0],
                 "support": "supported", "answer_text": "Enrollment opens January 4, 2027.",
                 "evidence": [{"evidence_id": evidence[0].evidence_id,
                               "quote": "Term A academic calendar. Enrollment opens January 4, 2027."}]}
        missing = json.dumps({"status": "answered", "parts": [first]})
        self.assertEqual(validate_selection(missing, evidence, question).status,
                         "insufficient_evidence")
        duplicate = dict(first, part_index=2)
        with self.assertRaises(ValueError):
            validate_selection(json.dumps({"status": "answered", "parts": [first, duplicate]}),
                               evidence, question)
        with self.assertRaises(ValueError):
            validate_selection(json.dumps({"status": "answered", "parts": [first, duplicate, duplicate]}),
                               evidence, question)

    def test_provider_cannot_supply_source_metadata(self):
        evidence = self.evidence((107, 1))
        question = "When does enrollment open?"
        part = {"part_index": 1, "part_text": _answer_question_parts(question)[0], "support": "supported",
                "answer_text": "Enrollment opens January 4, 2027.",
                "evidence": [{"evidence_id": evidence[0].evidence_id,
                              "quote": "Term A academic calendar. Enrollment opens January 4, 2027.",
                              "source_reference": "fictional://invented"}]}
        with self.assertRaises(ValueError):
            validate_selection(json.dumps({"status": "answered", "parts": [part]}),
                               evidence, question)

    def test_selection_diagnostics_classify_parser_schema_and_grounding_failures(self):
        evidence = self.evidence((107, 1))
        question = "When does Term A enrollment open?"
        part_text = _answer_question_parts(question)[0]
        valid_shape_bad_id = json.dumps({"status": "answered", "parts": [{
            "part_index": 1, "part_text": part_text, "support": "supported",
            "answer_text": "Enrollment opens January 4, 2027.",
            "evidence": [{"evidence_id": "private-do-not-log", "quote": "January 4, 2027"}],
        }]})
        incomplete = json.dumps({"status": "answered", "parts": [{
            "part_index": 1, "part_text": part_text, "support": "supported",
            "answer_text": "Orientation begins January 4, 2027.",
            "evidence": [{"evidence_id": evidence[0].evidence_id,
                          "quote": "Term A academic calendar. Enrollment opens January 4, 2027, and closes January 8, 2027."}],
        }]})
        for raw, expected, status in (("{malformed-do-not-log", "malformed_json", "unavailable"),
                                      ("{}", "schema_invalid", "unavailable"),
                                      (valid_shape_bad_id, "validation_failed", "unavailable"),
                                      (incomplete, "incomplete_answer", "insufficient_evidence")):
            with self.subTest(reason=expected):
                self.generator.reset_mock()
                self.generator.generate.return_value = raw
                with self.assertLogs("uvicorn.error", level="WARNING") as captured:
                    result = self.service(evidence).ask(question, reference_date=REFERENCE_DATE)
                events = [json.loads(record.getMessage()) for record in captured.records]
                failure = next(event for event in events if event.get("selection_reason"))
                self.assertEqual(failure["selection_reason"], expected)
                self.assertEqual(result.status, status)
                self.assertNotIn("do-not-log", " ".join(captured.output))


if __name__ == "__main__":
    unittest.main()
