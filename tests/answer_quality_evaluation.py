"""Offline, three-layer answer evaluation. The provider is always mocked."""

import json
import hashlib
import argparse
import re
import tempfile
from datetime import date
from decimal import Decimal
from pathlib import Path

from ai.answer_service import AnswerService, _ANSWER_CONNECTORS, _answer_question_parts, _format_money
from ai.demo_store import DemoStore
from ai.document_eligibility import load_fictional_documents
from ai.local_retrieval import Evidence, KeywordRetriever, _passage_tokens, _tokens


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "answer_quality_phase5.json"
DOCUMENTS = ROOT / "tests" / "fixtures" / "fictional_documents.json"
REFERENCE_DATE = date(2026, 11, 27)
MAX_QUOTE_CHARS = 180


class _FixedRetriever:
    def __init__(self, evidence):
        self.evidence = evidence

    def retrieve(self, _question, *, reference_date):
        return self.evidence


class _CaseGenerator:
    def __init__(self, case_by_question):
        self.case_by_question = case_by_question
        self.calls = 0
        self.output_chars = []

    def _serialized(self, payload):
        raw = json.dumps(payload, ensure_ascii=False)
        self.output_chars.append(len(raw))
        return raw

    @staticmethod
    def _candidate_windows(item):
        text = item.chunk.chunk_text
        candidates = []
        for sentence in re.split(r"(?<=[.!?;])\s+", text):
            sentence = sentence.strip()
            if not sentence:
                continue
            if len(sentence) <= MAX_QUOTE_CHARS:
                candidates.append(sentence)
            else:
                for start in range(0, len(sentence), MAX_QUOTE_CHARS - 35):
                    window = sentence[start:start + MAX_QUOTE_CHARS].strip()
                    if window:
                        candidates.append(window)
        if len(text) > MAX_QUOTE_CHARS:
            starts = list(range(0, len(text) - MAX_QUOTE_CHARS + 1, 45))
            starts.append(len(text) - MAX_QUOTE_CHARS)
            candidates.extend(text[start:start + MAX_QUOTE_CHARS].strip() for start in starts)
        return list(dict.fromkeys(candidates))

    def _quotes_for(self, answer_text, evidence):
        answer_terms = set(_tokens(answer_text)) - _ANSWER_CONNECTORS
        candidates = []
        for item in evidence:
            for quote in self._candidate_windows(item):
                source_terms = set(_passage_tokens(quote))
                candidates.append((len(answer_terms & source_terms), item, quote, source_terms))
        selected = []
        covered = set()
        for _ in range(2):
            best = max(candidates, key=lambda row: (len((answer_terms & row[3]) - covered), row[0]),
                       default=None)
            if best is None:
                break
            new_terms = (answer_terms & best[3]) - covered
            if not new_terms:
                break
            selected.append({"evidence_id": best[1].evidence_id, "quote": best[2]})
            covered.update(new_terms)
            candidates.remove(best)
        return selected

    def generate(self, question, evidence):
        self.calls += 1
        case = self.case_by_question[question]
        if case["expected_status"] != "answered":
            return self._serialized({"status": "insufficient_evidence", "parts": []})
        question_parts = _answer_question_parts(question)
        answer_texts = case.get("answer_texts", [])
        if len(question_parts) != len(answer_texts):
            return self._serialized({"status": "insufficient_evidence", "parts": []})
        parts = []
        for index, (part_text, answer_text) in enumerate(zip(question_parts, answer_texts), 1):
            selected_quotes = self._quotes_for(answer_text, evidence)
            if not selected_quotes:
                return self._serialized({"status": "insufficient_evidence", "parts": []})
            parts.append({
                "part_index": index,
                "part_text": part_text,
                "support": "supported",
                "answer_text": answer_text,
                "evidence": selected_quotes,
            })
        return self._serialized({"status": "answered", "parts": parts})


def _evidence_for_locators(chunks, groups):
    locators = []
    seen = set()
    for group in groups:
        if group:
            item = group[0]
            locator = (item["document_id"], item["page_no"])
            if locator not in seen:
                locators.append(locator)
                seen.add(locator)
    result = []
    for document_id, page_no in locators:
        chunk = next((item for item in chunks
                      if (item.document_id, item.page_no, item.chunk_index)
                      == (document_id, page_no, 0)), None)
        if chunk is not None and len(result) < 2:
            result.append(Evidence(f"e{len(result) + 1}", chunk, ()))
    return tuple(result)


def _group_coverage(groups, evidence):
    actual = {(item.chunk.document_id, item.chunk.page_no) for item in evidence}
    return [any((candidate["document_id"], candidate["page_no"]) in actual for candidate in group)
            for group in groups]


def _case_evaluation(case, evidence, generator, *, layer):
    service = AnswerService(_FixedRetriever(evidence), generator)
    response = service.ask(case["question"], reference_date=REFERENCE_DATE)
    groups = case.get("required_evidence_groups", [])
    coverage = _group_coverage(groups, evidence)
    retrieval_complete = bool(groups) and all(coverage)
    calculation = case.get("calculation")
    expected_amount = calculation.get("expected_amount") if calculation else None
    if calculation and calculation.get("expected_amounts"):
        expected_amounts = calculation["expected_amounts"]
    else:
        expected_amounts = []
    expected_values = ([expected_amount] if expected_amount else []) + expected_amounts
    amount_ok = all(_format_money(Decimal(value)) in response.answer for value in expected_values)
    amount_ok = amount_ok and all(
        phrase.casefold() in response.answer.casefold()
        for phrase in (calculation.get("required_output_phrases", []) if calculation else [])
    )
    answer_text_ok = all(text in response.answer for text in case.get("answer_texts", []))
    forbidden_present = [claim for claim in case.get("forbidden_claims", [])
                         if claim.casefold() in response.answer.casefold()]
    answer_text_ok = answer_text_ok and not forbidden_present
    if calculation:
        answer_text_ok = amount_ok
    return {
        "id": case["id"], "category": case["category"], "layer": layer,
        "expected_status": case["expected_status"], "actual_status": response.status,
        "retrieved": [[item.chunk.document_id, item.chunk.page_no, item.chunk.chunk_index]
                      for item in evidence],
        "required_evidence_groups": coverage,
        "retrieval_complete": retrieval_complete,
        "answer_complete": response.status == "answered" and answer_text_ok,
        "citation_locators": [[citation.document_id, citation.page_no, citation.chunk_index]
                              for citation in response.citations],
        "citations_valid": all((citation.document_id, citation.page_no, citation.chunk_index)
                               in {(item.chunk.document_id, item.chunk.page_no, item.chunk.chunk_index)
                                   for item in evidence}
                               for citation in response.citations),
        "forbidden_claims_present": forbidden_present,
        "answer": response.answer,
    }


def evaluate_answer_quality() -> dict:
    fixture_bytes = FIXTURE.read_bytes()
    fixture = json.loads(fixture_bytes.decode("utf-8"))
    cases = fixture["cases"]
    documents = load_fictional_documents(DOCUMENTS)
    direct_results, end_to_end_results = [], []
    mock_output_chars = []

    with tempfile.TemporaryDirectory(prefix="campuspilot-phase5-eval-") as directory:
        root = Path(directory).resolve()
        database_path = (root / "phase5-evaluation.sqlite3").resolve()
        store = DemoStore(database_path)
        try:
            store.initialize()
            store.seed(documents, reference_date=REFERENCE_DATE)
            chunks = store.public_chunks(reference_date=REFERENCE_DATE)
            real_retriever = KeywordRetriever(store)

            for case in cases:
                direct_evidence = _evidence_for_locators(chunks, case.get("required_evidence_groups", []))
                generator = _CaseGenerator({case["question"]: case})
                direct_results.append(_case_evaluation(case, direct_evidence, generator, layer="A"))
                mock_output_chars.extend(generator.output_chars)

                actual_evidence = real_retriever.retrieve(case["question"], reference_date=REFERENCE_DATE)
                e2e_generator = _CaseGenerator({case["question"]: case})
                end_to_end_results.append(_case_evaluation(
                    case, actual_evidence, e2e_generator, layer="B",
                ))
                mock_output_chars.extend(e2e_generator.output_chars)
        finally:
            store.close()

    supported = [case for case in cases if case["expected_status"] == "answered"]
    supported_ids = {case["id"] for case in supported}
    direct_by_id = {item["id"]: item for item in direct_results}
    e2e_by_id = {item["id"]: item for item in end_to_end_results}
    supported_direct = [direct_by_id[case_id] for case_id in supported_ids]
    supported_e2e = [e2e_by_id[case_id] for case_id in supported_ids]
    e2e_complete_retrieval = [item for item in supported_e2e if item["retrieval_complete"]]
    missing_evidence = [item for item in supported_e2e if not item["retrieval_complete"]]
    safe_abstentions = [item for item in missing_evidence
                        if item["actual_status"] == "insufficient_evidence"]
    wrong_accepts = [item for item in end_to_end_results
                     if item["expected_status"] != "answered" and item["actual_status"] == "answered"]
    answer_failures_with_evidence = [item for item in e2e_complete_retrieval
                                     if not item["answer_complete"]]
    return {
        "evaluation": "Phase 5 offline evaluation; mocked provider; no live model performance claimed.",
        "reference_date": fixture["reference_date"],
        "case_count": len(cases),
        "supported_case_count": len(supported),
        "fixture_sha256": hashlib.sha256(fixture_bytes).hexdigest(),
        "controlled_mock_completion_characters": {
            "samples": len(mock_output_chars),
            "maximum": max(mock_output_chars, default=0),
            "average": round(sum(mock_output_chars) / len(mock_output_chars), 2)
            if mock_output_chars else 0,
            "note": "Character counts are not provider-token measurements; live token use may differ.",
        },
        "layer_A_component": {
            "cases": direct_results,
            "supported_complete": sum(item["answer_complete"] for item in supported_direct),
            "supported_total": len(supported_direct),
            "citation_failures": sum(not item["citations_valid"] for item in direct_results),
        },
        "layer_B_end_to_end": {
            "cases": end_to_end_results,
            "supported_complete_retrieval": len(e2e_complete_retrieval),
            "supported_incomplete_retrieval": len(missing_evidence),
            "correct_answers_given_sufficient_evidence": sum(item["answer_complete"] for item in e2e_complete_retrieval),
            "safe_abstentions_due_to_missing_evidence": len(safe_abstentions),
            "incorrectly_accepted_unsupported": len(wrong_accepts),
            "answer_or_render_failures_with_complete_retrieval": len(answer_failures_with_evidence),
            "citation_failures": sum(not item["citations_valid"] for item in end_to_end_results),
        },
        "layer_C_live_model_plan": fixture["live_model_evaluation_plan"],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = evaluate_answer_quality()
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote offline answer-quality results: {args.output}")
    else:
        print(rendered)
