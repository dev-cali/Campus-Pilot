"""Temporary deterministic keyword retrieval, not embeddings or Pinecone."""

import re
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from ai.document_processing import DocumentChunk


MAX_QUESTION_CHARS = 2000
STOP_WORDS = frozenset({
    "a", "an", "and", "are", "at", "be", "can", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "me", "of", "on", "or", "please", "tell",
    "that", "the", "these", "this", "to", "was", "what", "when", "where",
    "which", "who", "with", "you", "your", "fictional", "demo", "campus", "university",
})


class PublicChunkSource(Protocol):
    """Storage interface: return only currently eligible public passages."""

    def public_chunks(self, *, reference_date: date) -> tuple[DocumentChunk, ...]:
        ...


@dataclass(frozen=True)
class Evidence:
    """Request-local citation ID plus trusted source data; score is not truth."""

    evidence_id: str
    chunk: DocumentChunk
    matched_terms: tuple[str, ...]


class Retriever(Protocol):
    """Future Pinecone adapter can return this same evidence contract.

    Every implementation must apply authoritative eligibility checks before
    returning content. The type declaration alone cannot enforce that rule.
    """

    def retrieve(self, question: str, *, reference_date: date) -> tuple[Evidence, ...]:
        ...


def validate_question(question: object) -> str:
    """Reject bad input with a fixed code; never silently truncate a question."""
    if not isinstance(question, str) or not question.strip():
        raise ValueError("invalid_question")
    if len(question) > MAX_QUESTION_CHARS:
        raise ValueError("question_too_long")
    return question.strip()


def _terms(text: str) -> set[str]:
    """Case-insensitive Unicode word matching; no stemming or synonym inference."""
    return set(re.findall(r"[^\W_]+", text.casefold())) - STOP_WORDS


class KeywordRetriever:
    """Search fresh eligible chunks; keep a bounded, deterministic candidate set.

    Source failures propagate to the future service layer. They must become
    'unavailable', not be disguised as a successful search with no evidence.
    """

    def __init__(self, source: PublicChunkSource, *, limit: int = 3):
        if type(limit) is not int or not 1 <= limit <= 5:
            raise ValueError("invalid_retrieval_limit")
        self.source = source
        self.limit = limit

    def retrieve(self, question: str, *, reference_date: date) -> tuple[Evidence, ...]:
        question = validate_question(question)
        if type(reference_date) is not date:
            raise ValueError("invalid_reference_date")
        terms = _terms(question)
        if not terms:
            return ()
        candidates = []
        for chunk in self.source.public_chunks(reference_date=reference_date):
            matches = tuple(sorted(terms & _terms(chunk.title + " " + chunk.chunk_text)))
            if matches:
                candidates.append((chunk, matches))
        candidates.sort(key=lambda item: (
            -len(item[1]), item[0].document_id, item[0].page_no, item[0].chunk_index,
        ))
        return tuple(
            Evidence(f"e{index}", chunk, matches)
            for index, (chunk, matches) in enumerate(candidates[:self.limit], start=1)
        )
