"""Optional, fail-safe Pinecone retrieval for the fictional demo corpus.

Pinecone IDs and scores are candidate hints only. All answer text and citation
metadata are resolved again from the currently eligible local SQLite chunks.
"""

from __future__ import annotations

import asyncio
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass, field
from datetime import date
import hashlib
import json
import logging
import os
import re
import time
from typing import Callable, Mapping
from urllib.parse import quote, urlsplit
from uuid import uuid4

from ai.document_eligibility import (
    load_fictional_documents,
    process_documents,
)
from ai.local_retrieval import (
    MAX_EVIDENCE_CHARS,
    MAX_EVIDENCE_CHUNKS,
    Evidence,
    KeywordRetriever,
    PublicChunkSource,
    Retriever,
    _is_personal_record_request,
    validate_evidence_budget,
    validate_question,
)


INDEX_NAME = "campuspilot-knowledge"
DEFAULT_NAMESPACE = "fictional-demo-v1"
EMBEDDING_FIELD = "chunk_text"
EXPECTED_MODEL = "llama-text-embed-v2"
EXPECTED_DIMENSION = 1024
EXPECTED_METRIC = "cosine"
MAX_SEMANTIC_CANDIDATES = 5
MIN_SEMANTIC_SCORE = 0.72
PER_ATTEMPT_TIMEOUT_SECONDS = 2.0
OVERALL_SEARCH_DEADLINE_SECONDS = 7.5

_semantic_cache: ContextVar[dict | None] = ContextVar("pinecone_semantic_cache", default=None)
_log = logging.getLogger("uvicorn.error")


@dataclass(frozen=True)
class PineconeSettings:
    api_key: str = field(repr=False)
    index_host: str
    namespace: str

    @classmethod
    def from_environment(cls) -> PineconeSettings | None:
        key = os.environ.get("PINECONE_API_KEY", "").strip()
        raw_host = os.environ.get("PINECONE_INDEX_HOST", "").strip()
        namespace = os.environ.get("PINECONE_NAMESPACE", DEFAULT_NAMESPACE).strip()
        host = _normalize_host(raw_host)
        if not key or not host or not namespace:
            return None
        return cls(key, host, namespace)


def _normalize_host(value: str) -> str | None:
    if not value:
        return None
    parsed = urlsplit(value if "://" in value else f"https://{value}")
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    if parsed.path not in ("", "/") or parsed.query or parsed.fragment:
        return None
    return parsed.netloc


def stable_record_id(chunk) -> str:
    """Stable source locator plus text digest, so stale same-version IDs fail closed."""
    version = quote(chunk.version or "", safe="-_.")
    digest = hashlib.sha256(chunk.chunk_text.encode("utf-8")).hexdigest()[:16]
    return f"cp-d{chunk.document_id}-v{version}-p{chunk.page_no}-c{chunk.chunk_index}-h{digest}"


def _identity(chunk) -> tuple[int, str, int, int]:
    return (chunk.document_id, chunk.version or "", chunk.page_no, chunk.chunk_index)


def _is_multipart(question: str) -> bool:
    # The answer service handles at most two explicit parts. Keep those requests
    # on the mature clause-aware keyword path until semantic coverage is tested.
    return bool(re.search(
        r";\s*|\band\s+(?=(?:when|what|who|where|how|which|whether|can|does|do|is)\b)",
        question,
        re.IGNORECASE,
    ))


def _emit(event: str, *, request_id: str, **fields) -> None:
    safe_fields = {"request_id": request_id, "category": event}
    for name in ("duration_ms", "candidate_count", "accepted_count", "selected_count"):
        value = fields.get(name)
        if type(value) is int and value >= 0:
            safe_fields[name] = value
    outcome = fields.get("outcome")
    if outcome in {
        "started", "completed", "configuration_missing", "search_failed",
        "timeout", "empty_results", "no_eligible_candidates", "below_threshold",
        "keyword_only", "multipart_keyword_only", "personal_request_keyword_only", "selected",
    }:
        safe_fields["outcome"] = outcome
    _log.warning("%s", json.dumps(safe_fields, separators=(",", ":")))


@contextmanager
def pinecone_request_scope():
    """Cache only remote candidate IDs for the answer service's stability recheck."""
    token = _semantic_cache.set({})
    try:
        yield
    finally:
        _semantic_cache.reset(token)


async def _sdk_search(settings: PineconeSettings, question: str):
    # Import lazily so keyword-only mode needs neither credentials nor SDK setup.
    from pinecone import AsyncIndex, EmbedQuery

    async with AsyncIndex(
        host=settings.index_host,
        api_key=settings.api_key,
        timeout=PER_ATTEMPT_TIMEOUT_SECONDS,
    ) as index:
        return await index.documents.search(
            namespace=settings.namespace,
            top_k=MAX_SEMANTIC_CANDIDATES,
            score_by=[EmbedQuery(field=EMBEDDING_FIELD, query=question)],
            include_fields=[],
            timeout=PER_ATTEMPT_TIMEOUT_SECONDS,
        )


def _match_id_score(match) -> tuple[str | None, float | None]:
    if isinstance(match, Mapping):
        identifier = match.get("_id", match.get("id"))
        score = match.get("_score", match.get("score"))
    else:
        identifier = getattr(match, "id", None)
        score = getattr(match, "score", None)
    if not isinstance(identifier, str):
        return None, None
    if isinstance(score, bool) or not isinstance(score, (int, float)):
        return identifier, None
    return identifier, float(score)


class PineconeRetriever:
    """Semantic candidates plus conservative local keyword fallback."""

    def __init__(
        self,
        source: PublicChunkSource,
        keyword_retriever: KeywordRetriever | None = None,
        *,
        settings: PineconeSettings | None = None,
        searcher: Callable[[PineconeSettings, str], object] | None = None,
        min_score: float = MIN_SEMANTIC_SCORE,
        overall_timeout: float = OVERALL_SEARCH_DEADLINE_SECONDS,
    ):
        if not 0.0 <= min_score <= 1.0 or overall_timeout <= 0:
            raise ValueError("invalid_pinecone_retrieval_limits")
        self.source = source
        self.keyword = keyword_retriever or KeywordRetriever(source)
        self.settings = settings or PineconeSettings.from_environment()
        self.searcher = searcher or _sdk_search
        self.min_score = min_score
        self.overall_timeout = overall_timeout

    @contextmanager
    def request_scope(self):
        with pinecone_request_scope():
            yield

    def _remote_candidates(self, question: str, reference_date: date, request_id: str):
        cache = _semantic_cache.get()
        cache_key = (question, reference_date, self.settings.namespace if self.settings else "")
        if cache is not None and cache_key in cache:
            return cache[cache_key]
        if self.settings is None:
            _emit("pinecone_fallback", request_id=request_id, outcome="configuration_missing")
            return ()

        started = time.monotonic()
        _emit("pinecone_search_started", request_id=request_id, outcome="started")
        try:
            async def bounded_search():
                result = self.searcher(self.settings, question)
                if hasattr(result, "__await__"):
                    return await asyncio.wait_for(result, timeout=self.overall_timeout)
                # Test doubles may be synchronous, but production uses AsyncIndex.
                return result

            response = asyncio.run(asyncio.wait_for(
                bounded_search(), timeout=self.overall_timeout,
            ))
            matches = getattr(response, "matches", None)
            if matches is None and isinstance(response, Mapping):
                matches = response.get("matches", ())
            candidates = tuple(_match_id_score(item) for item in (matches or ()))
            elapsed = round((time.monotonic() - started) * 1000)
            _emit("pinecone_search_completed", request_id=request_id,
                  outcome="completed", duration_ms=elapsed,
                  candidate_count=len(candidates))
            if cache is not None:
                cache[cache_key] = candidates
            return candidates
        except (asyncio.TimeoutError, TimeoutError):
            if cache is not None:
                cache[cache_key] = ()
            _emit("pinecone_fallback", request_id=request_id, outcome="timeout",
                  duration_ms=round((time.monotonic() - started) * 1000))
            return ()
        except Exception:
            # SDK errors are deliberately not formatted, logged, or returned.
            if cache is not None:
                cache[cache_key] = ()
            _emit("pinecone_fallback", request_id=request_id, outcome="search_failed",
                  duration_ms=round((time.monotonic() - started) * 1000))
            return ()

    def retrieve(self, question: str, *, reference_date: date) -> tuple[Evidence, ...]:
        question = validate_question(question)
        keyword_evidence = self.keyword.retrieve(question, reference_date=reference_date)
        if _is_personal_record_request(question):
            _emit("pinecone_fallback", request_id=uuid4().hex,
                  outcome="personal_request_keyword_only")
            return keyword_evidence
        if _is_multipart(question):
            _emit("pinecone_fallback", request_id=uuid4().hex,
                  outcome="multipart_keyword_only")
            return keyword_evidence
        if self.settings is None:
            _emit("pinecone_fallback", request_id=uuid4().hex,
                  outcome="configuration_missing")
            return keyword_evidence

        request_id = uuid4().hex
        candidates = self._remote_candidates(question, reference_date, request_id)
        local_chunks = self.source.public_chunks(reference_date=reference_date)
        by_record_id = {stable_record_id(chunk): chunk for chunk in local_chunks}
        local_identities = {_identity(chunk) for chunk in local_chunks}
        keyword_safe = [item for item in keyword_evidence
                        if _identity(item.chunk) in local_identities]
        selected = list(keyword_safe)
        selected_keys = {_identity(item.chunk) for item in selected}
        accepted = []
        locally_mapped = 0
        above_threshold = 0
        for identifier, score in candidates:
            if identifier is None or score is None:
                continue
            chunk = by_record_id.get(identifier)
            if chunk is None:  # Unknown, stale, or ineligible IDs are never trusted.
                continue
            locally_mapped += 1
            if score < self.min_score:
                continue
            above_threshold += 1
            key = _identity(chunk)
            if key in selected_keys:
                continue
            accepted.append((chunk, score))

        # Keep established keyword evidence first; semantic candidates only fill
        # remaining slots, without introducing a new ranking/fusion algorithm.
        for chunk, _score in accepted:
            if len(selected) >= MAX_EVIDENCE_CHUNKS:
                break
            proposed = [*selected, Evidence("candidate", chunk, ())]
            if sum(len(item.chunk.chunk_text) for item in proposed) > MAX_EVIDENCE_CHARS:
                continue
            selected.append(proposed[-1])
            selected_keys.add(_identity(chunk))

        if not accepted:
            outcome = (
                "empty_results" if not candidates else
                "no_eligible_candidates" if locally_mapped == 0 else
                "below_threshold" if above_threshold == 0 else "keyword_only"
            )
            _emit("pinecone_fallback", request_id=request_id,
                  outcome=outcome,
                  candidate_count=len(candidates))
        if len(selected) == len(keyword_safe):
            if accepted:
                _emit("pinecone_fallback", request_id=request_id, outcome="keyword_only",
                      candidate_count=len(candidates), accepted_count=len(accepted))
            return tuple(keyword_safe)

        evidence = tuple(Evidence(f"e{index}", item.chunk, item.matched_terms)
                         for index, item in enumerate(selected, start=1))
        try:
            validate_evidence_budget(evidence)
        except ValueError:
            _emit("pinecone_fallback", request_id=request_id,
                  outcome="no_eligible_candidates", candidate_count=len(candidates))
            return tuple(keyword_safe)
        _emit("pinecone_evidence_selected", request_id=request_id,
              outcome="selected", candidate_count=len(candidates),
              accepted_count=len(accepted), selected_count=len(evidence))
        return evidence


def create_retriever(source: PublicChunkSource) -> Retriever:
    """Use Pinecone only when explicitly selected; all other modes stay keyword-only."""
    mode = os.environ.get("AI_RETRIEVAL_MODE", "keyword_only").strip().lower()
    keyword = KeywordRetriever(source)
    if mode == "pinecone":
        return PineconeRetriever(source, keyword)
    return keyword


def check_index_schema(*, api_key: str, index_host: str) -> dict:
    """Authenticated read-only schema check; never returns the key or raw host."""
    from pinecone import Pinecone, RetryConfig

    expected_host = _normalize_host(index_host)
    if not expected_host:
        raise ValueError("invalid_pinecone_index_host")
    client = Pinecone(api_key=api_key, timeout=3.0,
                      retry_config=RetryConfig(max_retries=0))
    try:
        description = client.indexes.describe(INDEX_NAME)
        model_info = client.inference.model.get(model=EXPECTED_MODEL)
    finally:
        client.close()
    host = _normalize_host(getattr(description, "host", "") or "")
    schema = getattr(description, "schema", None)
    fields = getattr(schema, "fields", {}) or {}
    text_field = fields.get(EMBEDDING_FIELD) if isinstance(fields, Mapping) else None
    title_field = fields.get("title") if isinstance(fields, Mapping) else None
    if (host != expected_host or text_field is None or title_field is None
            or getattr(title_field, "full_text_search", None) is None):
        raise ValueError("pinecone_schema_mismatch")
    if getattr(text_field, "model", None) != EXPECTED_MODEL:
        raise ValueError("pinecone_schema_mismatch")
    if getattr(text_field, "metric", None) != EXPECTED_METRIC:
        raise ValueError("pinecone_schema_mismatch")
    configured_dimensions = []
    for parameters in (getattr(text_field, "read_parameters", None),
                       getattr(text_field, "write_parameters", None)):
        if isinstance(parameters, Mapping) and parameters.get("dimension") is not None:
            configured_dimensions.append(parameters["dimension"])
    if configured_dimensions:
        if any(value != EXPECTED_DIMENSION for value in configured_dimensions):
            raise ValueError("pinecone_schema_mismatch")
    elif getattr(model_info, "default_dimension", None) != EXPECTED_DIMENSION:
        raise ValueError("pinecone_schema_mismatch")
    if getattr(model_info, "type", None) != "embed":
        raise ValueError("pinecone_schema_mismatch")
    status = getattr(description, "status", None)
    if status is None or getattr(status, "ready", False) is not True:
        raise ValueError("pinecone_index_not_ready")
    return {"index": INDEX_NAME, "schema": "compatible", "ready": True}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Read-only Pinecone schema preflight")
    parser.add_argument("--check", action="store_true", help="check index schema without writing records")
    args = parser.parse_args()
    if not args.check:
        parser.error("use --check; this command never uploads records")
    settings = PineconeSettings.from_environment()
    if settings is None:
        raise SystemExit("Pinecone configuration is incomplete; no credentials were displayed.")
    try:
        print(json.dumps(check_index_schema(api_key=settings.api_key,
                                            index_host=settings.index_host)))
    except Exception:
        raise SystemExit("Pinecone schema preflight failed; SDK details were suppressed.") from None
