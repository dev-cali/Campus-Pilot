"""Small extractive answering service: model-selected quotes, backend checks.

Exact quote checks prevent newly invented wording, but cannot prove that a quote
answers the question or preserves all necessary context. This is not a semantic
verifier, production authorization system, or complete injection defense.
"""

import json
import re
from datetime import date
from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field

from ai.local_retrieval import Evidence, Retriever, validate_question, validate_evidence_budget
from ai.llm_client import DiagnosticFailure, diagnostic_event, diagnostic_request


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SelectedQuote(StrictModel):
    evidence_id: str = Field(min_length=1, max_length=20)
    quote: str = Field(min_length=1, max_length=300)


class ModelSelection(StrictModel):
    status: Literal["answered", "insufficient_evidence"]
    selections: list[SelectedQuote] = Field(max_length=2)


class Citation(StrictModel):
    evidence_id: str
    document_id: int
    page_no: int
    chunk_index: int
    title: str
    version: str
    source_reference: str


class AnswerResponse(StrictModel):
    status: Literal["answered", "insufficient_evidence", "unavailable", "denied"]
    answer: str = Field(min_length=1, max_length=4000)
    citations: list[Citation] = Field(max_length=3)
    fictional: Literal[True] = True


MESSAGES = {
    "insufficient_evidence": "The fictional demo documents do not provide enough verified information to answer this question.",
    "unavailable": "The fictional demo cannot verify an answer right now. Please try again later.",
    "denied": "This public fictional demo cannot provide that information.",
}


def fallback(status: Literal["insufficient_evidence", "unavailable", "denied"]) -> AnswerResponse:
    return AnswerResponse(status=status, answer=MESSAGES[status], citations=[])


class AnswerGenerator(Protocol):
    def generate(self, question: str, evidence: tuple[Evidence, ...]) -> str:
        """Return structured JSON, never trusted user-facing output."""
        ...


def _unique_json_object(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid_model_output")
        result[key] = value
    return result


def validate_selection(raw: str, evidence: tuple[Evidence, ...]) -> AnswerResponse:
    """Resolve metadata from supplied evidence and construct an extractive answer."""
    if not isinstance(raw, str) or len(raw) > 20000:
        raise ValueError("invalid_model_output")
    selection = ModelSelection.model_validate(json.loads(raw, object_pairs_hook=_unique_json_object))
    if selection.status == "insufficient_evidence":
        if selection.selections:
            raise ValueError("invalid_model_output")
        return fallback("insufficient_evidence")
    if not selection.selections:
        raise ValueError("invalid_model_output")
    by_id = {item.evidence_id: item.chunk for item in evidence}
    if len(by_id) != len(evidence):
        raise ValueError("invalid_evidence")
    citations, lines, used = [], [], set()
    for item in selection.selections:
        chunk = by_id.get(item.evidence_id)
        if chunk is None or item.evidence_id in used:
            raise ValueError("invalid_model_output")
        if not item.quote.strip() or item.quote not in chunk.chunk_text or not chunk.version:
            raise ValueError("invalid_model_output")
        used.add(item.evidence_id)
        citations.append(Citation(
            evidence_id=item.evidence_id, document_id=chunk.document_id,
            page_no=chunk.page_no, chunk_index=chunk.chunk_index, title=chunk.title,
            version=chunk.version, source_reference=chunk.source_reference,
        ))
        lines.append(f'[{item.evidence_id}] "{item.quote}"')
    return AnswerResponse(
        status="answered", answer="Fictional demo source excerpts:\n" + "\n".join(lines),
        citations=citations,
    )


class AnswerService:
    def __init__(self, retriever: Retriever, generator: AnswerGenerator, *, readiness_check=None):
        self.retriever = retriever
        self.generator = generator
        self.readiness_check = readiness_check

    def ask(self, question: str, *, reference_date: date) -> AnswerResponse:
        with diagnostic_request():
            return self._ask(question, reference_date=reference_date)

    def _ask(self, question: str, *, reference_date: date) -> AnswerResponse:
        question = validate_question(question)
        words = set(re.findall(r"\w+", question.casefold()))
        # Conservative demo scope signals, not authentication or an exhaustive
        # classifier. Source access is enforced separately by the retriever.
        if words & {"staff", "private", "password", "passwords", "secret", "secrets"}:
            return fallback("denied")
        if words & {"historical", "superseded", "previous", "older"}:
            return fallback("insufficient_evidence")
        failure_category = "retrieval_failed"
        try:
            if self.readiness_check is not None:
                self.readiness_check()
            evidence = self.retriever.retrieve(question, reference_date=reference_date)
            if not evidence:
                return fallback("insufficient_evidence")
            # Fail safely before paying for generation; preserve whole passages.
            failure_category = "evidence_invalid"
            try:
                validate_evidence_budget(evidence)
            except ValueError as error:
                # Match only our fixed local code; never log the exception itself.
                if error.args == ("evidence_budget_exceeded",):
                    failure_category = "evidence_budget_exceeded"
                raise
            text = " ".join(item.chunk.chunk_text for item in evidence).casefold()
            # Narrow absence checks for common factual requests. They do not
            # establish sufficiency, resolve conflicts, or understand negation.
            for term in ("gpa", "deadline", "fee", "amount"):
                if term in words and not re.search(r"\b" + term + r"\b", text):
                    return fallback("insufficient_evidence")
            failure_category = "provider_failed"
            raw = self.generator.generate(question, evidence)
            failure_category = "selection_invalid"
            answer = validate_selection(raw, evidence)
            if answer.status == "answered":
                # Fail closed if sources, permissions, or passage data changed
                # during generation. This does not eliminate every race window.
                failure_category = "retrieval_failed"
                fresh = self.retriever.retrieve(question, reference_date=reference_date)
                if fresh != evidence:
                    diagnostic_event("evidence_changed")
                    return fallback("unavailable")
            return answer
        except DiagnosticFailure as error:
            diagnostic_event(error.category, error.http_status,
                             provider_code=error.provider_code, provider_param=error.provider_param,
                             provider_classification=error.provider_classification,
                             provider_attribute_states=error.provider_attribute_states,
                             provider_response=error.provider_response)
            return fallback("unavailable")
        except Exception:
            # Deliberate application boundary: no provider/database error text,
            # raw model draft, source titles, or stack trace in student responses.
            diagnostic_event(failure_category)
            return fallback("unavailable")
