"""Schema and isolation checks for the offline, no-LLM retrieval evaluator."""

import json
import tempfile
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
from types import SimpleNamespace

from ai.demo_store import DEFAULT_DATABASE, DemoStore
from ai.document_eligibility import load_fictional_documents
from retrieval_evaluation import _apply_evidence_alternatives, _evaluate_set, evaluate


FIXTURES = Path(__file__).parent / "fixtures"


class RetrievalEvaluationTests(unittest.TestCase):
    def test_frozen_cases_have_approved_distribution_and_valid_source_locators(self):
        fixture = json.loads((FIXTURES / "retrieval_eval_cases.json").read_text(encoding="utf-8"))
        documents = load_fictional_documents(FIXTURES / "fictional_documents.json")
        pages = {document["document_id"]: {page["page_no"] for page in document["pages"]}
                 for document in documents}
        cases = fixture["primary_cases"]
        self.assertEqual(len(cases), 40)
        self.assertEqual(len(fixture["held_out_cases"]), 10)
        self.assertEqual(Counter(case["category"] for case in cases), Counter({
            "direct": 8, "procedural": 6, "paraphrased": 6, "two_part": 5,
            "multi_document": 5, "ambiguous": 3, "unsupported": 3, "security": 4,
        }))
        self.assertEqual(fixture["reference_date"], "2026-11-27")
        for case in cases + fixture["held_out_cases"]:
            with self.subTest(case=case["id"]):
                self.assertTrue(case["expected_facts"])
                for group in case["required_document_groups"]:
                    self.assertTrue(group)
                    self.assertTrue(all(document_id in pages for document_id in group))
                for group in case["required_evidence_groups"]:
                    self.assertTrue(group)
                    for alternative in group:
                        self.assertIn(alternative["document_id"], pages)
                        self.assertIn(alternative["page_no"], pages[alternative["document_id"]])
                for locator in case["expected_relevant_evidence"]:
                    self.assertIn(locator["document_id"], pages)
                    self.assertIn(locator["page_no"], pages[locator["document_id"]])

        additional = json.loads((FIXTURES / "retrieval_generalization_cases.json").read_text(
            encoding="utf-8"))
        self.assertEqual(len(additional["cases"]), 19)
        self.assertEqual(sum(case["supported"] for case in additional["cases"]), 16)
        self.assertIn("not an independently blind test", additional["description"])
        for case in additional["cases"]:
            for locator in case["expected_relevant_evidence"]:
                self.assertIn(locator["document_id"], pages)
                self.assertIn(locator["page_no"], pages[locator["document_id"]])

        validation = json.loads((FIXTURES / "retrieval_validation_phase4_2.json").read_text(
            encoding="utf-8"))
        self.assertEqual(len(validation["cases"]), 22)
        self.assertEqual(sum(case["supported"] for case in validation["cases"]), 20)
        self.assertIn("non-blind", validation["description"])
        for case in validation["cases"]:
            for locator in case["expected_relevant_evidence"]:
                self.assertIn(locator["document_id"], pages)
                self.assertIn(locator["page_no"], pages[locator["document_id"]])

        frozen_final = json.loads((FIXTURES / "retrieval_validation_phase4_3.json").read_text(
            encoding="utf-8"))
        self.assertEqual(len(frozen_final["cases"]), 22)
        self.assertEqual(sum(case["supported"] for case in frozen_final["cases"]), 20)
        self.assertIn("non-blind", frozen_final["description"])
        for case in frozen_final["cases"]:
            for locator in case["expected_relevant_evidence"]:
                self.assertIn(locator["document_id"], pages)
                self.assertIn(locator["page_no"], pages[locator["document_id"]])

        final_validation = json.loads((FIXTURES / "retrieval_validation_phase4_3.json").read_text(
            encoding="utf-8"))
        self.assertEqual(len(final_validation["cases"]), 22)
        self.assertEqual(sum(case["supported"] for case in final_validation["cases"]), 20)
        self.assertIn("non-blind", final_validation["description"])
        for case in final_validation["cases"]:
            for locator in case["expected_relevant_evidence"]:
                self.assertIn(locator["document_id"], pages)
                self.assertIn(locator["page_no"], pages[locator["document_id"]])

        phase44_final = json.loads((FIXTURES / "retrieval_validation_phase4_4_final.json").read_text(
            encoding="utf-8"))
        self.assertEqual(len(phase44_final["cases"]), 22)
        self.assertEqual(sum(case["supported"] for case in phase44_final["cases"]), 20)
        self.assertIn("Non-blind", phase44_final["description"])
        for case in phase44_final["cases"]:
            for locator in case["expected_relevant_evidence"]:
                self.assertIn(locator["document_id"], pages)
                self.assertIn(locator["page_no"], pages[locator["document_id"]])

    def test_evaluator_uses_temporary_database_and_keeps_api_out_of_scope(self):
        result = evaluate(iterations=1, implementation="phase4_3", primary_only=True)
        self.assertEqual(result["primary_case_count"], 40)
        self.assertEqual(result["held_out_case_count"], 0)
        self.assertFalse(result["held_out_included"])
        self.assertEqual(result["corpus_records"], 13)
        self.assertEqual(result["primary"]["evidence_budget_violations"], 0)
        self.assertEqual(result["primary"]["deterministic_ranking_rate"], 1.0)

    def test_current_implementation_is_labeled_and_ablation_is_temporary(self):
        from ai import local_retrieval

        original = local_retrieval.TITLE_WEIGHT
        result = evaluate(iterations=1, implementation="phase4_3", primary_only=True,
                          variant="without_title_weight")
        self.assertEqual(result["implementation"], "phase4_3")
        self.assertEqual(result["variant"], "without_title_weight")
        self.assertEqual(local_retrieval.TITLE_WEIGHT, original)

    def test_verified_alternatives_stay_in_one_fact_group(self):
        manifest_document = json.loads((FIXTURES / "equivalent_evidence_phase4_3.json").read_text(
            encoding="utf-8"))
        documents = load_fictional_documents(FIXTURES / "fictional_documents.json")
        with tempfile.TemporaryDirectory(prefix="campuspilot-equivalence-check-") as directory:
            root = Path(directory).resolve()
            database_path = (root / "equivalence.sqlite3").resolve()
            self.assertTrue(database_path.is_relative_to(root))
            self.assertNotEqual(database_path, DEFAULT_DATABASE.resolve())
            store = DemoStore(database_path)
            try:
                store.initialize()
                store.seed(documents, reference_date=date(2026, 11, 27))
                chunks = store.public_chunks(reference_date=date(2026, 11, 27))
                for correction in manifest_document["cases"]:
                    references = [
                        (correction["original_evidence"], correction["original_excerpt"]),
                        *zip(correction["acceptable_alternatives"],
                             [correction["alternative_excerpt"]]),
                    ]
                    for reference, excerpt in references:
                        matches = [chunk for chunk in chunks
                                   if (chunk.document_id, chunk.page_no, chunk.chunk_index)
                                   == (reference["document_id"], reference["page_no"],
                                       reference["chunk_index"])]
                        self.assertEqual(len(matches), 1)
                        self.assertIn(excerpt, matches[0].chunk_text)
            finally:
                store.close()

        cases = [{
            "id": "V04", "category": "equivalent_test", "question": "community award criteria",
            "expected_relevant_evidence": [{"document_id": 109, "page_no": 4},
                                            {"document_id": 111, "page_no": 1}],
            "required_evidence_groups": [[{"document_id": 109, "page_no": 4}],
                                          [{"document_id": 111, "page_no": 1}]],
            "supported": True, "expected_empty": False, "genuinely_multi_document": True,
        }]
        manifest = {"manifest_version": 1, "cases": [{
            "case_id": "V04",
            "original_evidence": {"document_id": 109, "page_no": 4, "chunk_index": 0},
            "acceptable_alternatives": [{"document_id": 109, "page_no": 1, "chunk_index": 0}],
        }]}
        corrected = _apply_evidence_alternatives(cases, manifest)
        self.assertEqual(len(corrected[0]["required_evidence_groups"]), 2)
        self.assertEqual(corrected[0]["required_evidence_groups"][0], [
            {"document_id": 109, "page_no": 4}, {"document_id": 109, "page_no": 1},
        ])
        self.assertEqual(corrected[0]["required_evidence_groups"][1],
                         [{"document_id": 111, "page_no": 1}])
        self.assertEqual(len(cases[0]["required_evidence_groups"][0]), 1)
        self.assertNotIn({"document_id": 109, "page_no": 2},
                         corrected[0]["required_evidence_groups"][0])

        phase44_manifest = json.loads((FIXTURES / "equivalent_evidence_phase4_4.json").read_text(
            encoding="utf-8"))
        for correction in phase44_manifest["cases"]:
            alternative = correction["acceptable_alternatives"][0]
            source = [chunk for chunk in chunks
                      if (chunk.document_id, chunk.page_no, chunk.chunk_index)
                      == (alternative["document_id"], alternative["page_no"],
                          alternative["chunk_index"])]
            self.assertEqual(len(source), 1)
            self.assertIn(correction["alternative_excerpt"], source[0].chunk_text)
        f19_cases = json.loads((FIXTURES / "retrieval_validation_phase4_3.json").read_text(
            encoding="utf-8"))["cases"]
        f19_cases = [case for case in f19_cases if case["id"] == "F19"]
        corrected_f19 = _apply_evidence_alternatives(f19_cases, phase44_manifest)
        self.assertEqual(len(corrected_f19[0]["required_evidence_groups"]), 2)
        self.assertEqual(corrected_f19[0]["required_evidence_groups"][0], [
            {"document_id": 107, "page_no": 2},
            {"document_id": 113, "page_no": 3},
        ])
        self.assertEqual(corrected_f19[0]["required_evidence_groups"][1], [
            {"document_id": 113, "page_no": 3},
        ])

        class StubRetriever:
            def __init__(self, locators):
                self.locators = locators

            def retrieve(self, _question, *, reference_date):
                return tuple(SimpleNamespace(chunk=SimpleNamespace(
                    document_id=document_id, page_no=page_no, chunk_index=0,
                    chunk_text="verified fictional passage",
                ), matched_terms=()) for document_id, page_no in self.locators)

        equivalent_only = _evaluate_set(
            StubRetriever([(109, 1)]), corrected, 1, date(2026, 11, 27),
        )
        self.assertEqual(equivalent_only["required_evidence_groups"], 2)
        self.assertEqual(equivalent_only["required_evidence_coverage"], 0.5)
        self.assertEqual(equivalent_only["complete_retrieval_success_supported"], 0.0)

        both_equivalent_passages = _evaluate_set(
            StubRetriever([(109, 4), (109, 1), (111, 1)]), corrected, 1,
            date(2026, 11, 27),
        )
        self.assertEqual(both_equivalent_passages["required_evidence_groups"], 2)
        self.assertEqual(both_equivalent_passages["required_evidence_coverage"], 1.0)
        self.assertEqual(both_equivalent_passages["irrelevant_chunks"], 0)

        different_award = _evaluate_set(
            StubRetriever([(109, 2)]), corrected, 1, date(2026, 11, 27),
        )
        self.assertEqual(different_award["required_evidence_coverage"], 0.0)
        self.assertEqual(different_award["irrelevant_chunks"], 1)

        unrelated = _evaluate_set(
            StubRetriever([(101, 1)]), corrected, 1, date(2026, 11, 27),
        )
        self.assertEqual(unrelated["irrelevant_chunks"], 1)


if __name__ == "__main__":
    unittest.main()
