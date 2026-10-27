"""Offline fictional-source eligibility; not production authentication.

The catalog and permissions must be supplied by trusted calling code. Decisions
are internal diagnostics, not a student-facing document-discovery API.
"""

import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Optional

from ai.document_processing import DocumentChunk, split_document_text


STATUSES = frozenset({"approved", "draft", "revoked"})
ACCESS_LEVELS = frozenset({"public", "staff"})
VERSION_STATES = frozenset({"current", "superseded"})
REQUIRED_FIELDS = frozenset({
    "fictional", "institution", "document_id", "title", "version", "status",
    "access_level", "effective_date", "source_reference", "version_state", "pages",
})


@dataclass(frozen=True)
class EligibilityDecision:
    """No document IDs, titles, source links, page text, or input values."""

    eligible: bool
    reason: str


@dataclass(frozen=True)
class ProcessingResult:
    """Internal result: decisions align with input order; chunks are permitted."""

    decisions: tuple[EligibilityDecision, ...]
    chunks: tuple[DocumentChunk, ...]


def _positive_integer(value: object) -> bool:
    return type(value) is int and value > 0


def _parse_date(value: object) -> Optional[date]:
    """Accept only canonical YYYY-MM-DD strings, without coercing input."""
    if not isinstance(value, str):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return parsed if parsed.isoformat() == value else None


def validate_document(document: object) -> EligibilityDecision:
    """Check the entire record, including every page, without exposing values.

    A valid record is not necessarily eligible: approval/access/date checks
    belong to evaluate_documents. 'valid_metadata' never means permission.
    """
    invalid = EligibilityDecision(False, "invalid_metadata")
    if not isinstance(document, dict):
        return invalid
    if not REQUIRED_FIELDS <= document.keys():
        return invalid
    if document.keys() - (REQUIRED_FIELDS | {"supersedes"}):
        return invalid
    if document["fictional"] is not True:
        return invalid
    if document["institution"] != "Demo Campus University":
        return invalid
    if not _positive_integer(document["document_id"]):
        return invalid
    for field in ("title", "version", "source_reference"):
        value = document[field]
        if not isinstance(value, str) or not value.strip():
            return invalid
    # These are opaque local fixture references, never fetched or rendered URLs.
    if not document["source_reference"].startswith("fictional://demo-campus/"):
        return invalid
    for field, allowed in (("status", STATUSES), ("access_level", ACCESS_LEVELS),
                           ("version_state", VERSION_STATES)):
        if not isinstance(document[field], str) or document[field] not in allowed:
            return invalid
    if _parse_date(document["effective_date"]) is None:
        return invalid
    predecessor = document.get("supersedes")
    if "supersedes" in document:
        if not _positive_integer(predecessor) or predecessor == document["document_id"]:
            return invalid
    pages = document["pages"]
    if not isinstance(pages, list) or not pages:
        return invalid
    for number, page in enumerate(pages, start=1):
        if not isinstance(page, dict) or set(page) != {"page_no", "text"}:
            return invalid
        if not _positive_integer(page["page_no"]) or page["page_no"] != number:
            return invalid
        if not isinstance(page["text"], str) or not page["text"].strip():
            return invalid
    return EligibilityDecision(True, "valid_metadata")


def _catalog_is_consistent(documents: list) -> bool:
    """Reject ambiguous IDs, missing predecessors, and supersession cycles."""
    by_id = {document["document_id"]: document for document in documents}
    if len(by_id) != len(documents):
        return False
    for document in documents:
        seen = set()
        current = document
        while "supersedes" in current:
            identifier = current["document_id"]
            predecessor = current["supersedes"]
            if identifier in seen or predecessor not in by_id:
                return False
            seen.add(identifier)
            previous = by_id[predecessor]
            if _parse_date(previous["effective_date"]) > _parse_date(current["effective_date"]):
                return False
            current = previous
    return True


def evaluate_documents(
    documents: list, *, trusted_permissions: object, reference_date: object,
    query_mode: str = "current",
) -> tuple[EligibilityDecision, ...]:
    """Evaluate a complete trusted catalog in order, with fail-closed defaults.

    Pass a set/frozenset of explicit access grants, e.g. {'public'} or
    {'public', 'staff'}. No role inference or permission inheritance occurs.
    A malformed catalog closes the whole batch because it may hide supersession.
    """
    if not isinstance(documents, list):
        return (EligibilityDecision(False, "invalid_catalog"),)

    def reject_all(reason: str) -> tuple[EligibilityDecision, ...]:
        return tuple(EligibilityDecision(False, reason) for _ in documents)

    if query_mode != "current":
        return reject_all("unsupported_query_mode")
    if type(reference_date) is not date:
        return reject_all("invalid_reference_date")
    if not isinstance(trusted_permissions, (set, frozenset)):
        return reject_all("invalid_permissions")
    if not trusted_permissions or not trusted_permissions <= ACCESS_LEVELS:
        return reject_all("invalid_permissions")
    if any(not validate_document(document).eligible for document in documents):
        return reject_all("invalid_catalog")
    if not _catalog_is_consistent(documents):
        return reject_all("invalid_catalog")

    # Conservative: any explicit replacement blocks its predecessor, even when
    # the replacement is draft/future/revoked/restricted. Never revive old policy.
    superseded_ids = {doc["supersedes"] for doc in documents if "supersedes" in doc}
    decisions = []
    for document in documents:
        if document["access_level"] not in trusted_permissions:
            reason = "access_denied"
        elif document["status"] != "approved":
            reason = "not_approved"
        elif (document["version_state"] != "current"
              or document["document_id"] in superseded_ids):
            reason = "superseded"
        elif _parse_date(document["effective_date"]) > reference_date:
            reason = "not_yet_effective"
        else:
            reason = "eligible"
        decisions.append(EligibilityDecision(reason == "eligible", reason))
    return tuple(decisions)


def process_documents(
    documents: list, *, trusted_permissions: object, reference_date: object,
    query_mode: str = "current", max_chars: int = 1000,
) -> ProcessingResult:
    """Validate the whole batch first, then pass only eligible pages to PR #8."""
    if not _positive_integer(max_chars):
        raise ValueError("invalid_chunk_limit")
    decisions = evaluate_documents(
        documents, trusted_permissions=trusted_permissions,
        reference_date=reference_date, query_mode=query_mode,
    )
    chunks = []
    if isinstance(documents, list):
        for document, decision in zip(documents, decisions):
            if not decision.eligible:
                continue
            for page in document["pages"]:
                chunks.extend(split_document_text(
                    page["text"], document_id=document["document_id"],
                    page_no=page["page_no"], title=document["title"],
                    source_reference=document["source_reference"],
                    version=document["version"], max_chars=max_chars,
                ))
    return ProcessingResult(decisions, tuple(chunks))


def _unique_object(pairs: list) -> dict:
    """Do not let JSON silently replace duplicate approval/access fields."""
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("invalid_fixture")
        result[key] = value
    return result


def load_fictional_documents(path: str | Path) -> list:
    """Read local JSON; errors contain neither file contents nor local paths.

    Loading is not eligibility. Always use process_documents afterwards.
    """
    try:
        documents = json.loads(
            Path(path).read_text(encoding="utf-8"), object_pairs_hook=_unique_object,
        )
    except (OSError, UnicodeError, ValueError, TypeError):
        raise ValueError("invalid_fixture") from None
    if not isinstance(documents, list):
        raise ValueError("invalid_fixture")
    return documents
