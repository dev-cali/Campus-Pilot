"""Explicit MOCK backend for UI demonstrations. Never calls a provider.

Run from repository root: python -B -m tests.frontend_demo_server is not required;
use the documented runpy command because tests is not a Python package.
"""

import argparse
import json
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

import uvicorn

from ai.answer_service import AnswerService
from ai.demo_api import create_app
from ai.demo_store import DEFAULT_FIXTURE, DemoStore
from ai.document_eligibility import load_fictional_documents
from ai.local_retrieval import KeywordRetriever


class MockGenerator:
    def generate(self, _question, evidence):
        # Deterministic integration fixture, NOT evidence of real model reasoning.
        supported_questions = {
            "What sample course list do fictional learners review for enrollment?",
            "What do fictional learners review for enrollment?",
        }
        quote = "Demo Campus University asks imaginary learners to review a sample course list in this exercise."
        chosen = next((item for item in evidence if quote in item.chunk.chunk_text), None)
        if _question not in supported_questions or chosen is None:
            return json.dumps({"status": "insufficient_evidence", "parts": []})
        return json.dumps({"status": "answered", "parts": [{
            "part_index": 1, "part_text": _question, "support": "supported",
            "evidence_id": chosen.evidence_id, "quote": quote,
        }]})


class LabeledMockService(AnswerService):
    def ask(self, question, *, reference_date):
        result = super().ask(question, reference_date=reference_date)
        result.answer = "[MOCK DEMONSTRATION — no LLM call]\n" + result.answer
        return result


def main():
    parser = argparse.ArgumentParser(description="Mock-only CampusPilot frontend test server")
    parser.add_argument("--port", type=int, default=8012)
    args = parser.parse_args()
    with TemporaryDirectory() as directory:
        store = DemoStore(Path(directory) / "mock.sqlite3")
        try:
            store.initialize()
            store.seed(load_fictional_documents(DEFAULT_FIXTURE), reference_date=date(2026, 10, 26))
            service = LabeledMockService(KeywordRetriever(store), MockGenerator())
            app = create_app(service, reference_date=date(2026, 10, 26))
            app.title = "CampusPilot MOCK demonstration — no LLM calls"
            uvicorn.run(app, host="127.0.0.1", port=args.port)
        finally:
            store.close()


if __name__ == "__main__":
    main()
