"""Deterministic retrieval-only evaluation; never calls an LLM or hosted service."""

import argparse
import hashlib
import json
import statistics
import subprocess
import sys
import tempfile
import time
import types
from contextlib import contextmanager
from collections import defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.demo_store import DEFAULT_DATABASE, DemoStore
from ai.document_eligibility import load_fictional_documents
import ai.local_retrieval as local_retrieval
from ai.local_retrieval import KeywordRetriever, MAX_EVIDENCE_CHARS, MAX_EVIDENCE_CHUNKS


EVALUATION_FIXTURE = ROOT / "tests" / "fixtures" / "retrieval_eval_cases.json"
GENERALIZATION_FIXTURE = ROOT / "tests" / "fixtures" / "retrieval_generalization_cases.json"
VALIDATION_FIXTURE = ROOT / "tests" / "fixtures" / "retrieval_validation_phase4_2.json"
FINAL_VALIDATION_FIXTURE = ROOT / "tests" / "fixtures" / "retrieval_validation_phase4_3.json"
PHASE4_4_FINAL_VALIDATION_FIXTURE = ROOT / "tests" / "fixtures" / "retrieval_validation_phase4_4_final.json"
DOCUMENT_FIXTURE = ROOT / "tests" / "fixtures" / "fictional_documents.json"
EXCLUDED_IDS = {102, 104, 105, 106}


def locator(item):
    return (item["document_id"], item["page_no"])


def _evaluate_set(retriever, cases, iterations, reference_date):
    results = []
    latency_samples_ms = []
    total_groups = 0
    covered_groups = 0
    total_document_groups = 0
    covered_document_groups = 0
    supported_cases = 0
    complete_cases = 0
    returned_chunks = 0
    relevant_chunks = 0
    irrelevant_chunks = 0
    redundant_chunks = 0
    first_result_hits = 0
    expected_empty_cases = 0
    expected_empty_false_positives = 0
    excluded_leak_cases = 0
    budget_violations = 0
    deterministic_cases = 0
    category_counts = defaultdict(lambda: {"cases": 0, "complete": 0})
    genuine_multidoc = {"cases": 0, "complete": 0}
    paraphrase = {"cases": 0, "complete": 0}

    for case in cases:
        query_times = []
        retrieval_sequences = []
        evidence = ()
        for _ in range(iterations):
            started = time.perf_counter_ns()
            evidence = retriever.retrieve(case["question"], reference_date=reference_date)
            query_times.append((time.perf_counter_ns() - started) / 1_000_000)
            retrieval_sequences.append(tuple(
                (item.chunk.document_id, item.chunk.page_no, item.chunk.chunk_index)
                for item in evidence
            ))
        latency_samples_ms.extend(query_times)

        actual = [locator({"document_id": item.chunk.document_id,
                           "page_no": item.chunk.page_no}) for item in evidence]
        actual_set = set(actual)
        relevant = {locator(item) for item in case["expected_relevant_evidence"]}
        required_groups = [set(locator(item) for item in group)
                           for group in case["required_evidence_groups"]]
        group_covered = [bool(group & actual_set) for group in required_groups]
        required_document_groups = [set(group) for group in case.get("required_document_groups", [])]
        document_group_covered = [
            bool(group & {document_id for document_id, _page in actual})
            for group in required_document_groups
        ]
        group_count = len(required_groups)
        covered = sum(group_covered)
        complete = group_count > 0 and covered == group_count
        deterministic = all(sequence == retrieval_sequences[0]
                            for sequence in retrieval_sequences[1:])
        deterministic_cases += int(deterministic)

        total_groups += group_count
        covered_groups += covered
        total_document_groups += len(required_document_groups)
        covered_document_groups += sum(document_group_covered)
        category = case["category"]
        category_counts[category]["cases"] += int(group_count > 0)
        category_counts[category]["complete"] += int(complete)
        if case["supported"] and group_count:
            supported_cases += 1
            complete_cases += int(complete)
            first_result_hits += int(bool(actual and actual[0] in relevant))
        if case["genuinely_multi_document"]:
            genuine_multidoc["cases"] += 1
            genuine_multidoc["complete"] += int(complete)
        if category == "paraphrased":
            paraphrase["cases"] += 1
            paraphrase["complete"] += int(complete)

        case_relevant = sum(item in relevant for item in actual)
        case_irrelevant = len(actual) - case_relevant
        # A relevant second result is redundant when it does not satisfy a new
        # required group. Optional context for a case with no required groups
        # (for example, a fictional-scope disclaimer) is not labelled redundant.
        covered_so_far = set()
        case_redundant = 0
        for item in actual:
            newly_covered = {index for index, group in enumerate(required_groups)
                             if item in group and index not in covered_so_far}
            if item in relevant and required_groups and not newly_covered:
                case_redundant += 1
            covered_so_far.update(newly_covered)
        returned_chunks += len(actual)
        relevant_chunks += case_relevant
        irrelevant_chunks += case_irrelevant
        redundant_chunks += case_redundant
        first_hit = bool(actual and actual[0] in relevant)

        expected_empty_cases += int(case["expected_empty"])
        expected_empty_false_positives += int(case["expected_empty"] and bool(actual))
        excluded_leak = any(document_id in EXCLUDED_IDS for document_id, _ in actual)
        excluded_leak_cases += int(excluded_leak)
        budget_violations += int(
            len(evidence) > MAX_EVIDENCE_CHUNKS
            or sum(len(item.chunk.chunk_text) for item in evidence) > MAX_EVIDENCE_CHARS
        )
        results.append({
            "id": case["id"],
            "category": category,
            "question": case["question"],
            "expected_groups": [[list(item) for item in sorted(group)]
                                for group in required_groups],
            "expected_relevant": [list(item) for item in sorted(relevant)],
            "retrieved": [
                {"document_id": item.chunk.document_id,
                 "page_no": item.chunk.page_no,
                 "chunk_index": item.chunk.chunk_index,
                 "matched_terms": list(item.matched_terms)}
                for item in evidence
            ],
            "groups_covered": group_covered,
            "complete_required_evidence": complete,
            "deterministic": deterministic,
            "irrelevant_count": case_irrelevant,
            "redundant_count": case_redundant,
            "first_result_relevant": first_hit,
            "expected_empty_false_positive": bool(case["expected_empty"] and actual),
            "excluded_document_returned": excluded_leak,
            "latency_median_ms": round(statistics.median(query_times), 4),
        })

    def ratio(numerator, denominator):
        return round(numerator / denominator, 4) if denominator else None

    return {
        "case_count": len(cases),
        "required_evidence_groups": total_groups,
        "required_document_groups": total_document_groups,
        "required_documents_retrieved_at_top_two": covered_document_groups,
        "required_document_recall_at_top_two": ratio(
            covered_document_groups, total_document_groups),
        "required_evidence_coverage": ratio(covered_groups, total_groups),
        "complete_retrieval_success_supported": ratio(complete_cases, supported_cases),
        "supported_case_count": supported_cases,
        "precision_at_returned_evidence": ratio(relevant_chunks, returned_chunks),
        "returned_chunks": returned_chunks,
        "relevant_chunks": relevant_chunks,
        "irrelevant_evidence_rate": ratio(irrelevant_chunks, returned_chunks),
        "irrelevant_chunks": irrelevant_chunks,
        "redundant_relevant_chunks": redundant_chunks,
        "first_result_accuracy_supported": ratio(first_result_hits, supported_cases),
        "paraphrase_complete_retrieval": {
            "successes": paraphrase["complete"], "cases": paraphrase["cases"],
            "rate": ratio(paraphrase["complete"], paraphrase["cases"]),
        },
        "genuine_multi_document_coverage": {
            "successes": genuine_multidoc["complete"], "cases": genuine_multidoc["cases"],
            "rate": ratio(genuine_multidoc["complete"], genuine_multidoc["cases"]),
        },
        "expected_empty_false_positive_rate": ratio(
            expected_empty_false_positives, expected_empty_cases),
        "expected_empty_cases": expected_empty_cases,
        "expected_empty_false_positives": expected_empty_false_positives,
        "security_exclusion_rate": 1.0 if excluded_leak_cases == 0 else 0.0,
        "excluded_leak_cases": excluded_leak_cases,
        "evidence_budget_violations": budget_violations,
        "deterministic_ranking_rate": ratio(deterministic_cases, len(cases)),
        "deterministic_cases": deterministic_cases,
        "latency_ms": {
            "iterations_per_case": iterations,
            "measurement_includes_db_read_and_revalidation": True,
            "database_initialization_excluded": True,
            "median": round(statistics.median(latency_samples_ms), 4),
            "p95": round(sorted(latency_samples_ms)[int(0.95 * (len(latency_samples_ms) - 1))], 4),
            "maximum": round(max(latency_samples_ms), 4),
            "samples": len(latency_samples_ms),
        },
        "category_complete_rates": {
            name: {"complete": values["complete"], "supported_cases": values["cases"],
                   "rate": ratio(values["complete"], values["cases"])}
            for name, values in sorted(category_counts.items())
        },
        "cases": results,
    }


def _apply_evidence_alternatives(cases, manifest):
    """Apply verified locator alternatives inside their original evidence group."""
    copied = json.loads(json.dumps(cases))
    by_id = {case["id"]: case for case in copied}
    for correction in manifest.get("cases", []):
        case = by_id.get(correction["case_id"])
        if case is None:
            continue
        original = correction["original_evidence"]
        matches = [
            group for group in case["required_evidence_groups"]
            if any(locator(item) == locator(original) for item in group)
        ]
        if len(matches) != 1:
            raise ValueError("alternative_original_group_ambiguous")
        group = matches[0]
        for alternative in correction.get("acceptable_alternatives", []):
            if alternative.get("chunk_index") != 0:
                raise ValueError("alternative_chunk_index_not_supported_by_evaluator")
            page_locator = locator(alternative)
            if not any(locator(item) == page_locator for item in group):
                group.append({"document_id": alternative["document_id"],
                              "page_no": alternative["page_no"]})
            relevant = case.setdefault("expected_relevant_evidence", [])
            if not any(locator(item) == page_locator for item in relevant):
                relevant.append({"document_id": alternative["document_id"],
                                 "page_no": alternative["page_no"]})
    return copied


def _phase3_retriever_class(source=None):
    if source is None:
        source = subprocess.run(
        ["git", "show", "fa5c5bc:ai/local_retrieval.py"],
        cwd=ROOT, check=True, capture_output=True, text=True,
        ).stdout
    module = types.ModuleType("campuspilot_phase3_local_retrieval")
    module.__file__ = "fa5c5bc:ai/local_retrieval.py"
    sys.modules[module.__name__] = module
    exec(compile(source, module.__file__, "exec"), module.__dict__)
    return module.KeywordRetriever


@contextmanager
def _ablation(variant):
    """Temporarily toggle one scoring mechanism for controlled offline tests."""
    settings = {
        "baseline": {},
        "without_expansions": {"_PHRASE_EXPANSIONS": ()},
        "without_title_weight": {"TITLE_WEIGHT": 0.0},
        "relaxed_relevance_threshold": {"MIN_RELEVANCE_SCORE": 1.0},
        "without_event_bonuses": {
            "_numeric_answer_bonus": lambda *_args, **_kwargs: 0.0,
            "_dated_event_bonus": lambda *_args, **_kwargs: 0.0,
            "_event_attribute_bonus": lambda *_args, **_kwargs: 0.0,
        },
        "one_evidence_chunk": {"MAX_EVIDENCE_CHUNKS": 1},
    }
    if variant not in settings:
        raise ValueError("unknown_retrieval_ablation")
    old = {name: getattr(local_retrieval, name) for name in settings[variant]}
    try:
        for name, value in settings[variant].items():
            setattr(local_retrieval, name, value)
        yield
    finally:
        for name, value in old.items():
            setattr(local_retrieval, name, value)


def evaluate(iterations=20, implementation="phase4_3", primary_only=False,
             dataset="standard", variant="baseline", alternatives_manifest=None):
    if implementation not in {"phase3", "phase4_3"}:
        raise ValueError("historical_retriever_must_use_preserved_results")
    if implementation == "phase3" and variant != "baseline":
        raise ValueError("ablations_require_current_implementation")
    fixture_path = {
        "standard": EVALUATION_FIXTURE,
        "generalization": GENERALIZATION_FIXTURE,
        "validation": VALIDATION_FIXTURE,
        "final_validation": FINAL_VALIDATION_FIXTURE,
        "phase4_4_final": PHASE4_4_FINAL_VALIDATION_FIXTURE,
    }.get(dataset)
    if fixture_path is None:
        raise ValueError("unknown_retrieval_dataset")
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    manifest = None
    manifest_bytes = None
    if alternatives_manifest is not None:
        manifest_path = Path(alternatives_manifest)
        if not manifest_path.is_absolute():
            manifest_path = ROOT / manifest_path
        manifest_bytes = manifest_path.read_bytes()
        manifest = json.loads(manifest_bytes.decode("utf-8"))
        if manifest.get("manifest_version") != 1:
            raise ValueError("unsupported_alternative_manifest_version")
    reference_date = date.fromisoformat(fixture["reference_date"])
    documents = load_fictional_documents(DOCUMENT_FIXTURE)
    source_text = subprocess.run(
        ["git", "show", "fa5c5bc:ai/local_retrieval.py"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout if implementation == "phase3" else None
    source_bytes = source_text.encode("utf-8") if source_text is not None else (ROOT / "ai" / "local_retrieval.py").read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    retriever_class = (_phase3_retriever_class(source_text)
                       if implementation == "phase3" else KeywordRetriever)
    results = {}
    with _ablation(variant):
        with tempfile.TemporaryDirectory(prefix="campuspilot-retrieval-eval-") as directory:
            temp_root = Path(directory).resolve()
            database_path = (temp_root / "retrieval.sqlite3").resolve()
            if not database_path.is_relative_to(temp_root):
                raise RuntimeError("evaluation_database_path_outside_temp_directory")
            if database_path == DEFAULT_DATABASE.resolve():
                raise RuntimeError("evaluation_database_is_default_store")
            store = DemoStore(database_path)
            if store.path != database_path or not store.path.is_relative_to(temp_root):
                raise RuntimeError("resolved_evaluation_database_path_invalid")
            try:
                store.initialize()
                store.seed(documents, reference_date=reference_date)
                retriever = retriever_class(store)
                if dataset in {"generalization", "validation", "final_validation", "phase4_4_final"}:
                    selected_cases = fixture["cases"]
                    if manifest is not None:
                        selected_cases = _apply_evidence_alternatives(selected_cases, manifest)
                    results[dataset] = _evaluate_set(
                        retriever, selected_cases, iterations, reference_date,
                    )
                else:
                    primary_cases = fixture["primary_cases"]
                    held_out_cases = fixture["held_out_cases"]
                    if manifest is not None:
                        primary_cases = _apply_evidence_alternatives(primary_cases, manifest)
                        held_out_cases = _apply_evidence_alternatives(held_out_cases, manifest)
                    results["primary"] = _evaluate_set(
                        retriever, primary_cases, iterations, reference_date,
                    )
                if dataset == "standard" and not primary_only:
                    results["held_out"] = _evaluate_set(
                        retriever, held_out_cases, iterations, reference_date,
                    )
            finally:
                store.close()
    return {
        "reference_date": fixture["reference_date"],
        "implementation": implementation,
        "implementation_source_sha256": source_hash,
        "evaluation_fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "alternative_manifest_sha256": (hashlib.sha256(manifest_bytes).hexdigest()
                                         if manifest_bytes is not None else None),
        "evaluator_source_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "variant": variant,
        "dataset": dataset,
        "dataset_classification": {
            "standard": "frozen_primary_and_held_out",
            "generalization": "diagnostic_non_blind",
            "validation": "final_non_blind",
            "final_validation": "post_freeze_final_non_blind",
        "phase4_4_final": "post_freeze_final_non_blind_phase4_4",
        }[dataset],
        "corpus_records": len(documents),
        "primary_case_count": (len(fixture["primary_cases"])
                               if dataset == "standard" else 0),
        "held_out_case_count": (0 if primary_only or dataset != "standard"
                                else len(fixture["held_out_cases"])),
        "held_out_included": dataset == "standard" and not primary_only,
        "generalization_case_count": len(fixture["cases"])
                                     if dataset == "generalization" else 0,
        "validation_case_count": len(fixture["cases"])
                                 if dataset == "validation" else 0,
        "final_validation_case_count": len(fixture["cases"])
                                      if dataset == "final_validation" else 0,
        "phase4_4_final_case_count": len(fixture["cases"])
                                     if dataset == "phase4_4_final" else 0,
        "iterations_per_case": iterations,
        **({"primary": results["primary"]} if dataset == "standard" else {}),
        **({dataset: results["generalization"]}
           if dataset == "generalization" else {}),
        **({"validation": results["validation"]} if dataset == "validation" else {}),
        **({"final_validation": results["final_validation"]}
           if dataset == "final_validation" else {}),
        **({"phase4_4_final": results["phase4_4_final"]}
           if dataset == "phase4_4_final" else {}),
        **({"held_out": results["held_out"]}
           if dataset == "standard" and not primary_only else {}),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=20)
    parser.add_argument("--implementation", choices=("phase3", "phase4_3"), default="phase4_3")
    parser.add_argument("--dataset", choices=("standard", "generalization", "validation", "final_validation", "phase4_4_final"), default="standard")
    parser.add_argument("--alternatives-manifest", type=Path)
    parser.add_argument("--variant", choices=("baseline", "without_expansions",
                        "without_title_weight", "relaxed_relevance_threshold",
                        "without_event_bonuses", "one_evidence_chunk"), default="baseline")
    parser.add_argument("--primary-only", action="store_true",
                        help="evaluate only the frozen 40-case primary set during iteration")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.iterations < 1:
        parser.error("--iterations must be positive")
    result = evaluate(args.iterations, args.implementation, args.primary_only,
                      args.dataset, args.variant, args.alternatives_manifest)
    rendered = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
        print(f"Wrote offline retrieval results: {args.output}")
    else:
        print(rendered)


if __name__ == "__main__":
    main()
