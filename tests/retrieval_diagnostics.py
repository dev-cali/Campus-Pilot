"""Local-only scoring traces for fictional retrieval evaluation questions."""

import argparse
import hashlib
import json
import sys
import tempfile
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from ai.demo_store import DEFAULT_DATABASE, DemoStore
from ai.document_eligibility import load_fictional_documents
from ai.local_retrieval import KeywordRetriever


def diagnose(output: Path) -> None:
    generalization_path = ROOT / "tests" / "fixtures" / "retrieval_generalization_cases.json"
    retrieval_path = ROOT / "tests" / "fixtures" / "retrieval_eval_cases.json"
    validation_path = ROOT / "tests" / "fixtures" / "retrieval_validation_phase4_2.json"
    document_path = ROOT / "tests" / "fixtures" / "fictional_documents.json"
    generalization = json.loads(generalization_path.read_text(encoding="utf-8"))
    standard = json.loads(retrieval_path.read_text(encoding="utf-8"))
    validation = json.loads(validation_path.read_text(encoding="utf-8"))
    references = {
        case["id"]: case for case in generalization["cases"]
    }
    references.update({
        case["id"]: case for case in standard["held_out_cases"]
        if case["id"] in {"H04", "H10"}
    })
    references.update({
        case["id"]: case for case in validation["cases"]
        if case["id"] in {"V04", "V05", "V06", "V07", "V09", "V11", "V19"}
    })
    reference_date = date.fromisoformat(generalization["reference_date"])
    documents = load_fictional_documents(document_path)
    traces = []
    with tempfile.TemporaryDirectory(prefix="campuspilot-retrieval-diagnostics-") as directory:
        root = Path(directory).resolve()
        database_path = (root / "diagnostics.sqlite3").resolve()
        if not database_path.is_relative_to(root) or database_path == DEFAULT_DATABASE.resolve():
            raise RuntimeError("diagnostic_database_path_invalid")
        store = DemoStore(database_path)
        try:
            store.initialize()
            store.seed(documents, reference_date=reference_date)
            for case_id, case in references.items():
                events = []
                retriever = KeywordRetriever(store, _diagnostics=events.append)
                evidence = retriever.retrieve(case["question"], reference_date=reference_date)
                traces.append({
                    "case_id": case_id,
                    "expected_evidence_groups": case["required_evidence_groups"],
                    "expected_relevant_evidence": case["expected_relevant_evidence"],
                    "final_evidence": [
                        {"document_id": item.chunk.document_id,
                         "page_no": item.chunk.page_no,
                         "chunk_index": item.chunk.chunk_index}
                        for item in evidence
                    ],
                    "events": events,
                })
        finally:
            store.close()
    output.write_text(json.dumps({
        "implementation": "phase4_3",
        "implementation_source_sha256": hashlib.sha256(
            (ROOT / "ai" / "local_retrieval.py").read_bytes()
        ).hexdigest(),
        "dataset": "diagnostic_not_blind",
        "reference_date": reference_date.isoformat(),
        "case_count": len(traces),
        "cases": traces,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    diagnose(args.output)


if __name__ == "__main__":
    main()
