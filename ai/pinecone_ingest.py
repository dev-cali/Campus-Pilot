"""Explicit, fictional-only ingestion into the Pinecone demo namespace.

Dry-run is the default. Nothing is uploaded unless ``--apply`` is supplied.
This module is never called by ``start-ai.sh`` or application startup.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
import time
from pathlib import Path

from ai.document_eligibility import load_fictional_documents, process_documents
from ai.demo_store import DEFAULT_FIXTURE
from ai.pinecone_retrieval import (
    DEFAULT_NAMESPACE,
    PineconeSettings,
    check_index_schema,
    stable_record_id,
)


EXPECTED_RECORD_COUNT = 23


def build_records(reference_date: date, fixture: Path = DEFAULT_FIXTURE) -> tuple[list[dict], int]:
    documents = load_fictional_documents(fixture)
    processed = process_documents(
        documents, trusted_permissions={"public"}, reference_date=reference_date,
    )
    if any(not decision.eligible and decision.reason in {"invalid_catalog", "invalid_reference_date"}
           for decision in processed.decisions):
        raise ValueError("invalid_fictional_catalog")
    by_id = {document["document_id"]: document for document in documents}
    records = []
    for chunk in processed.chunks:
        document = by_id.get(chunk.document_id)
        if not document or document["status"] != "approved" or document["access_level"] != "public":
            raise ValueError("ineligible_chunk_rejected")
        records.append({
            "_id": stable_record_id(chunk),
            "chunk_text": chunk.chunk_text,
            "title": chunk.title,
            "document_id": chunk.document_id,
            "version": chunk.version,
            "page_no": chunk.page_no,
            "chunk_index": chunk.chunk_index,
            "source_reference": chunk.source_reference,
            "visibility": document["access_level"],
            "approval_status": document["status"],
            "version_state": document["version_state"],
            "effective_date": document["effective_date"],
            "fictional": True,
            "content_sha256": hashlib.sha256(chunk.chunk_text.encode("utf-8")).hexdigest(),
        })
    if len(records) != EXPECTED_RECORD_COUNT or len({item["_id"] for item in records}) != len(records):
        raise ValueError("unexpected_fictional_record_inventory")
    return records, sum(decision.eligible for decision in processed.decisions)


def _document_ids(index, namespace: str) -> set[str]:
    return {item.id for item in index.documents.list(namespace=namespace)}


def ingest(*, apply: bool = False, settings: PineconeSettings | None = None,
           reference_date: date | None = None, index_factory=None,
           wait_seconds: float = 45.0, sleep=time.sleep) -> dict:
    date_for_records = reference_date or datetime.now(timezone.utc).date()
    records, eligible_documents = build_records(date_for_records)
    expected_ids = {record["_id"] for record in records}
    active_settings = settings or PineconeSettings.from_environment()
    if not apply:
        return {"dry_run": True, "eligible_documents": eligible_documents,
                "expected_records": len(records), "namespace":
                active_settings.namespace if active_settings else DEFAULT_NAMESPACE}
    if active_settings is None:
        raise ValueError("pinecone_configuration_missing")
    check_index_schema(api_key=active_settings.api_key, index_host=active_settings.index_host)
    client = None
    if index_factory is None:
        from pinecone import Pinecone
        client = Pinecone(api_key=active_settings.api_key, timeout=5.0)
        index = client.index(host=active_settings.index_host)
    else:
        index = index_factory(active_settings)

    try:
        existing_ids = _document_ids(index, active_settings.namespace)
        unexpected = existing_ids - expected_ids
        if unexpected:
            raise ValueError("namespace_contains_unexpected_records")

        index.documents.upsert(namespace=active_settings.namespace, documents=records)
        deadline = time.monotonic() + wait_seconds
        visible_ids = set()
        while time.monotonic() < deadline:
            visible_ids = _document_ids(index, active_settings.namespace)
            if visible_ids == expected_ids:
                return {"dry_run": False, "eligible_documents": eligible_documents,
                        "verified_records": len(visible_ids), "namespace": active_settings.namespace}
            sleep(1)
        raise TimeoutError("pinecone_record_visibility_timeout")
    finally:
        close = getattr(index, "close", None)
        if callable(close):
            close()
        if client is not None:
            client.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Explicit fictional-corpus Pinecone ingestion")
    parser.add_argument("--apply", action="store_true", help="upload after schema and namespace checks")
    parser.add_argument("--reference-date", type=date.fromisoformat)
    args = parser.parse_args()
    try:
        print(ingest(apply=args.apply, reference_date=args.reference_date))
    except Exception:
        raise SystemExit("Pinecone ingestion failed; diagnostic details were suppressed.") from None


if __name__ == "__main__":
    main()
