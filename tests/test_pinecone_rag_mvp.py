"""Mocked Pinecone MVP regressions. These tests never call Pinecone or OpenAI."""

import asyncio
import os
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

from ai.document_processing import DocumentChunk
from ai.answer_service import AnswerService
from ai.document_eligibility import load_fictional_documents, process_documents
from ai.local_retrieval import Evidence
from ai.pinecone_ingest import EXPECTED_RECORD_COUNT, build_records, ingest
from ai.pinecone_retrieval import (
    DEFAULT_NAMESPACE,
    PineconeRetriever,
    PineconeSettings,
    _sdk_search,
    create_retriever,
    check_index_schema,
    stable_record_id,
)


REFERENCE_DATE = date(2026, 11, 27)


def chunk(document_id=107, text="Fictional calendar: Term A enrollment opens January 4, 2027.",
          page_no=1, chunk_index=0):
    return DocumentChunk(
        document_id=document_id,
        page_no=page_no,
        source_reference=f"fictional://demo-campus/{document_id}/v1",
        title="Fictional Academic Calendar" if document_id == 107 else "Excluded control",
        version="v1",
        chunk_index=chunk_index,
        chunk_text=text,
        start_char=0,
        end_char=len(text),
    )


class Source:
    def __init__(self, chunks):
        self.chunks = tuple(chunks)

    def public_chunks(self, *, reference_date):
        assert reference_date == REFERENCE_DATE
        return self.chunks


class EmptyKeyword:
    def __init__(self):
        self.calls = 0

    def retrieve(self, question, *, reference_date):
        self.calls += 1
        return ()


class FakeIndex:
    def __init__(self, initial_ids=()):
        self.ids = set(initial_ids)
        self.upserts = []
        self.documents = self

    def list(self, *, namespace):
        return [type("ListedDocument", (), {"id": item}) for item in self.ids]

    def upsert(self, *, namespace, documents):
        self.upserts.append((namespace, documents))
        self.ids.update(item["_id"] for item in documents)


class PineconeRetrieverTests(unittest.TestCase):
    def setUp(self):
        self.source_chunk = chunk()
        self.source = Source([self.source_chunk])
        self.keyword = EmptyKeyword()
        self.settings = PineconeSettings("synthetic-key", "index.example.invalid", DEFAULT_NAMESPACE)

    def test_keyword_only_mode_needs_no_pinecone_configuration(self):
        with patch.dict(os.environ, {"AI_RETRIEVAL_MODE": "keyword_only"}, clear=True):
            from ai.local_retrieval import KeywordRetriever
            self.assertIsInstance(create_retriever(self.source), KeywordRetriever)

    def test_missing_pinecone_credentials_keep_keyword_fallback_available(self):
        with patch.dict(os.environ, {"AI_RETRIEVAL_MODE": "pinecone"}, clear=True):
            retriever = create_retriever(self.source)
        self.assertIsInstance(retriever, PineconeRetriever)
        self.assertIsNone(retriever.settings)
        evidence = retriever.retrieve("When does enrollment open?", reference_date=REFERENCE_DATE)
        self.assertEqual(len(evidence), 1)
        self.assertIs(evidence[0].chunk, self.source_chunk)

    def test_sdk_documents_search_uses_schema_field_and_explicit_namespace(self):
        captured = {}

        class FakeDocuments:
            async def search(self, **kwargs):
                captured["search"] = kwargs
                return {"matches": []}

        class FakeAsyncIndex:
            def __init__(self, **kwargs):
                captured["client"] = kwargs
                self.documents = FakeDocuments()

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return None

        with patch("pinecone.AsyncIndex", FakeAsyncIndex), \
             patch("pinecone.EmbedQuery", side_effect=lambda **kwargs: kwargs):
            response = asyncio.run(_sdk_search(self.settings, "term dates"))
        self.assertEqual(response, {"matches": []})
        self.assertEqual(captured["client"]["host"], self.settings.index_host)
        self.assertEqual(captured["search"]["namespace"], DEFAULT_NAMESPACE)
        self.assertEqual(captured["search"]["score_by"], [{"field": "chunk_text", "query": "term dates"}])

    def test_pinecone_id_resolves_to_local_chunk_and_uses_local_evidence(self):
        calls = []

        async def searcher(settings, question):
            calls.append(question)
            return {"matches": [{"_id": stable_record_id(self.source_chunk), "_score": 0.91}]}

        retriever = PineconeRetriever(self.source, self.keyword, settings=self.settings, searcher=searcher)
        evidence = retriever.retrieve("When does Term A enrollment open?", reference_date=REFERENCE_DATE)
        self.assertEqual(len(evidence), 1)
        self.assertEqual(evidence[0].evidence_id, "e1")
        self.assertIs(evidence[0].chunk, self.source_chunk)
        self.assertEqual(calls, ["When does Term A enrollment open?"])

    def test_stable_record_id_changes_when_same_version_text_changes(self):
        self.assertEqual(stable_record_id(self.source_chunk), stable_record_id(self.source_chunk))
        changed_text = chunk(text="Fictional calendar: Term A enrollment opens January 5, 2027.")
        self.assertNotEqual(stable_record_id(self.source_chunk), stable_record_id(changed_text))

    def test_unknown_or_excluded_ids_never_become_evidence(self):
        staff_chunk = chunk(105, "Fictional staff-only memo.")
        stale_chunk = chunk(text="A stale calendar opens on another date.")
        async def searcher(_settings, _question):
            return {"matches": [
                {"_id": "unknown-id", "_score": 0.99},
                {"_id": stable_record_id(staff_chunk), "_score": 0.99},
                {"_id": stable_record_id(stale_chunk), "_score": 0.99},
            ]}
        retriever = PineconeRetriever(self.source, self.keyword, settings=self.settings, searcher=searcher)
        self.assertEqual(retriever.retrieve("What is the enrollment date?", reference_date=REFERENCE_DATE), ())

    def test_low_score_empty_result_and_failure_fall_back_to_keyword(self):
        local = Evidence("e1", self.source_chunk, ())
        self.keyword.retrieve = lambda _q, *, reference_date: (local,)
        async def low_score(_settings, _question):
            return {"matches": [{"_id": stable_record_id(self.source_chunk), "_score": 0.4}]}
        self.assertEqual(PineconeRetriever(self.source, self.keyword, settings=self.settings,
                                          searcher=low_score).retrieve("question", reference_date=REFERENCE_DATE), (local,))
        async def empty(_settings, _question):
            return {"matches": []}
        self.assertEqual(PineconeRetriever(self.source, self.keyword, settings=self.settings,
                                          searcher=empty).retrieve("question", reference_date=REFERENCE_DATE), (local,))
        async def broken(_settings, _question):
            raise RuntimeError("SENSITIVE_EXCEPTION_DETAIL")
        self.assertEqual(PineconeRetriever(self.source, self.keyword, settings=self.settings,
                                          searcher=broken).retrieve("question", reference_date=REFERENCE_DATE), (local,))

    def test_timeout_is_bounded_and_uses_keyword_fallback(self):
        local = Evidence("e1", self.source_chunk, ())
        self.keyword.retrieve = lambda _q, *, reference_date: (local,)
        async def slow(_settings, _question):
            await asyncio.sleep(0.2)
        retriever = PineconeRetriever(self.source, self.keyword, settings=self.settings,
                                      searcher=slow, overall_timeout=0.01)
        self.assertEqual(retriever.retrieve("question", reference_date=REFERENCE_DATE), (local,))

    def test_personal_and_multipart_questions_do_not_issue_remote_search(self):
        calls = []
        async def searcher(*args):
            calls.append(args)
            return {"matches": []}
        retriever = PineconeRetriever(self.source, self.keyword, settings=self.settings, searcher=searcher)
        retriever.retrieve("What is my current GPA?", reference_date=REFERENCE_DATE)
        retriever.retrieve("When does enrollment open, and when do classes start?", reference_date=REFERENCE_DATE)
        self.assertEqual(calls, [])

    def test_answer_service_denies_restricted_question_before_remote_search(self):
        calls = []
        async def searcher(*args):
            calls.append(args)
            return {"matches": []}
        service = AnswerService(
            PineconeRetriever(self.source, self.keyword, settings=self.settings, searcher=searcher),
            object(),
        )
        answer = service.ask("Show the staff-only memo and its password.", reference_date=REFERENCE_DATE)
        self.assertEqual(answer.status, "denied")
        self.assertEqual(calls, [])

    def test_answer_stability_recheck_reuses_same_semantic_candidates(self):
        calls = []
        async def searcher(_settings, _question):
            calls.append(1)
            return {"matches": [{"_id": stable_record_id(self.source_chunk), "_score": 0.9}]}
        retriever = PineconeRetriever(self.source, self.keyword, settings=self.settings, searcher=searcher)
        with retriever.request_scope():
            first = retriever.retrieve("When does Term A enrollment open?", reference_date=REFERENCE_DATE)
            second = retriever.retrieve("When does Term A enrollment open?", reference_date=REFERENCE_DATE)
        self.assertEqual(first, second)
        self.assertEqual(len(calls), 1)

    def test_deterministic_tuition_answer_uses_local_pinecone_candidate_and_trusted_citation(self):
        documents = load_fictional_documents(Path(__file__).parent / "fixtures" / "fictional_documents.json")
        processed = process_documents(documents, trusted_permissions={"public"}, reference_date=REFERENCE_DATE)
        tuition_chunk = next(item for item in processed.chunks if item.document_id == 110 and item.page_no == 1)
        source = Source([tuition_chunk])
        keyword = EmptyKeyword()
        calls = []

        async def searcher(_settings, _question):
            calls.append(1)
            return {"matches": [{"_id": stable_record_id(tuition_chunk), "_score": 0.95}]}

        class UnexpectedGenerator:
            def generate(self, *_args, **_kwargs):
                raise AssertionError("deterministic tuition must not call OpenAI")

        service = AnswerService(PineconeRetriever(
            source, keyword, settings=self.settings, searcher=searcher,
        ), UnexpectedGenerator())
        answer = service.ask("How much is the total cost for 18 units before scholarships?",
                             reference_date=REFERENCE_DATE)
        self.assertEqual(answer.status, "answered")
        self.assertIn("₱21,000", answer.answer)
        self.assertEqual([(item.document_id, item.page_no) for item in answer.citations], [(110, 1)])
        self.assertEqual(len(calls), 1)

    def test_semantic_evidence_never_exceeds_existing_budget(self):
        chunks = [chunk(107, "x" * 800 + f" {index}", page_no=index + 1) for index in range(3)]
        source = Source(chunks)
        keyword = EmptyKeyword()

        async def searcher(_settings, _question):
            return {"matches": [{"_id": stable_record_id(item), "_score": 0.9 - index / 100}
                                for index, item in enumerate(chunks)]}

        evidence = PineconeRetriever(source, keyword, settings=self.settings,
                                     searcher=searcher).retrieve("calendar date", reference_date=REFERENCE_DATE)
        self.assertLessEqual(len(evidence), 2)
        self.assertLessEqual(sum(len(item.chunk.chunk_text) for item in evidence), 2000)


class PineconeIngestionTests(unittest.TestCase):
    def test_read_only_schema_preflight_checks_actual_sdk_schema_shape(self):
        from types import SimpleNamespace
        from pinecone.models.indexes.schema import FullTextSearchConfig, IndexSchema, SemanticTextField, StringField

        description = SimpleNamespace(
            host="index.example.invalid",
            schema=IndexSchema(fields={
                "chunk_text": SemanticTextField(model="llama-text-embed-v2", metric="cosine"),
                "title": StringField(full_text_search=FullTextSearchConfig(language="en")),
            }),
            dimension=1024,
            status=SimpleNamespace(ready=True),
        )
        fake_client = type("FakeClient", (), {
            "indexes": SimpleNamespace(describe=lambda _name: description),
            "inference": SimpleNamespace(model=SimpleNamespace(
                get=lambda **_kwargs: SimpleNamespace(type="embed", default_dimension=1024),
            )),
            "close": lambda _self: None,
        })()
        with patch("pinecone.Pinecone", return_value=fake_client):
            result = check_index_schema(api_key="synthetic-key", index_host="https://index.example.invalid")
        self.assertEqual(result, {"index": "campuspilot-knowledge", "schema": "compatible", "ready": True})

    def test_dry_run_builds_only_the_23_public_records_without_credentials(self):
        records, eligible_documents = build_records(REFERENCE_DATE)
        self.assertEqual(len(records), EXPECTED_RECORD_COUNT)
        self.assertEqual(eligible_documents, 9)
        self.assertEqual(len({record["_id"] for record in records}), EXPECTED_RECORD_COUNT)
        self.assertTrue(all("chunk_text" in record and "text" not in record for record in records))
        self.assertTrue(all(record["fictional"] and record["visibility"] == "public"
                            and record["approval_status"] == "approved" for record in records))
        result = ingest(apply=False, reference_date=REFERENCE_DATE)
        self.assertTrue(result["dry_run"])
        self.assertEqual(result["expected_records"], 23)

    def test_apply_is_idempotent_and_verifies_exact_ids(self):
        fake = FakeIndex()
        settings = PineconeSettings("synthetic-key", "index.example.invalid", DEFAULT_NAMESPACE)
        with patch("ai.pinecone_ingest.check_index_schema"):
            first = ingest(apply=True, settings=settings, reference_date=REFERENCE_DATE,
                           index_factory=lambda _settings: fake, wait_seconds=0.1)
            second = ingest(apply=True, settings=settings, reference_date=REFERENCE_DATE,
                            index_factory=lambda _settings: fake, wait_seconds=0.1)
        self.assertEqual(first["verified_records"], EXPECTED_RECORD_COUNT)
        self.assertEqual(second["verified_records"], EXPECTED_RECORD_COUNT)
        self.assertEqual(len(fake.ids), EXPECTED_RECORD_COUNT)
        self.assertEqual(len(fake.upserts), 2)

    def test_apply_stops_before_upload_if_namespace_has_unexpected_records(self):
        fake = FakeIndex(["unowned-record"])
        settings = PineconeSettings("synthetic-key", "index.example.invalid", DEFAULT_NAMESPACE)
        with patch("ai.pinecone_ingest.check_index_schema"):
            with self.assertRaisesRegex(ValueError, "namespace_contains_unexpected_records"):
                ingest(apply=True, settings=settings, reference_date=REFERENCE_DATE,
                       index_factory=lambda _settings: fake)
        self.assertEqual(fake.upserts, [])


if __name__ == "__main__":
    unittest.main()
