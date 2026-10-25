# S3-01: Offline Document Eligibility and Guardrails Foundation

## Purpose and implemented scope

CampusPilot needs to check whether a source may be used before preparing it for
AI retrieval. This academic prototype uses **Demo Campus University**, a fictional
institution. Every fixture record and page is labeled fictional. No real student
records, real university policies, credentials, or paid services are needed.

Implemented in [document_eligibility.py](../ai/document_eligibility.py): metadata
validation, explicit approval/access/version/date checks, safe decisions, local
JSON loading, and integration with the existing [PR #8 chunker](../ai/document_processing.py).
This is an offline eligibility foundation, **not production authentication or a
complete RAG system**. A Python caller can supply false permissions or metadata;
the code cannot prove that the caller is trusted.

```text
Trusted fictional JSON catalog + explicit permissions + reference date
  -> validate complete catalog and replacement links
  -> check approval, access, version state, and effective date
  -> eligible page text only
  -> existing document chunker
  -> chunks retaining source metadata
```

## Fictional document contract

[fictional_documents.json](../tests/fixtures/fictional_documents.json) is a JSON
array. The array is assumed to be the complete, trusted prototype catalog, not
an arbitrary search result or student upload. JSON objects with duplicate keys
are rejected rather than silently allowing a later value to override approval.
Unknown record/page fields are rejected to catch misspellings and accidental
permission fields. Missing required fields fail closed (no processing).

| Field | Rule and meaning |
| --- | --- |
| `fictional` | Required JSON `true`; a label, not a privacy detector |
| `institution` | Exactly `Demo Campus University` |
| `document_id` | Positive integer, not a boolean; unique in the catalog; each version has its own ID |
| `title` | Nonblank string; preserved exactly |
| `version` | Required nonblank string; opaque label, never sorted to guess currency |
| `status` | Exactly `approved`, `draft`, or `revoked` |
| `access_level` | Exactly `public` or `staff` |
| `effective_date` | Valid canonical `YYYY-MM-DD` date; inclusive start date |
| `source_reference` | Nonblank string beginning `fictional://demo-campus/`; opaque local reference, never fetched; not a production citation URL validator |
| `version_state` | Required `current` or `superseded`; explicit trusted prototype assertion of currency |
| `supersedes` | Optional positive predecessor document ID; cannot be null, self, or absent from the catalog |
| `pages` | Nonempty array of objects containing only `page_no` and `text`; nonblank text; consecutive page numbers starting at 1, no duplicates or gaps |

The extra `version_state` field is deliberate: a version label and an old
effective date do not prove current authority. This assertion must come from
authoritative backend records in a future integration. The prototype does not
discover undeclared replacement relationships or verify whether two documents
describe the same policy. It cannot detect a maliciously incomplete catalog.

## Approval and permissions

Only `approved` records can pass. Draft and revoked records cannot pass even for
staff. Access grants are supplied separately as a Python `set` or `frozenset`:

- `{"public"}`: explicit public/student scope for the demonstration.
- `{"public", "staff"}`: explicitly authorized staff plus public scope.
- `{"staff"}`: staff documents only; no implicit public grant.

Missing, empty, unknown, string, list, or dictionary permissions fail closed.
There is no role lookup, password, department filter, network call, or
authentication endpoint. A department selected in a UI is not permission.
Never populate `trusted_permissions` directly from a student request.

## Versions, dates, and conservative decisions

The caller must pass a Python `date` explicitly; strings, datetimes, and missing
dates are rejected. The implementation never reads the current clock. A document
effective on the supplied date may pass; a future-effective document cannot.
The caller's date describes the current snapshot being evaluated, not a request
to reconstruct historical policy.

Only `query_mode="current"` is supported. Historical and unknown modes return
`unsupported_query_mode` and no chunks. Passing an earlier date does not restore
superseded versions. Historical selection needs a separate future design.

A record marked `superseded` is excluded. Any document explicitly referenced by
another record's `supersedes` is also excluded even if its own flag says current.
This is conservative: a future, draft, revoked, or restricted replacement still
blocks its predecessor. The system does not automatically revive old guidance.
This may produce no eligible policy and needs Brian/content-owner approval.

Duplicate IDs, missing predecessors, cycles, or a replacement dated before its
predecessor invalidate the entire catalog. Any malformed record also blocks the
whole batch, so a malformed replacement cannot be silently ignored while its old
version is used. This favors safety over availability for the small prototype.
It is not a general policy conflict resolver or a scalable indexing algorithm.

## Functions and results in simple English

| Function | What it does |
| --- | --- |
| `validate_document` | Checks one record's shape, fields, and every page. `valid_metadata` means the record is shaped correctly, not approved for use. |
| `evaluate_documents` | Checks the complete catalog and returns one `EligibilityDecision` per input record, in input order. A non-list input returns one `invalid_catalog` decision. An empty list returns no decisions. |
| `process_documents` | Evaluates the batch first; only then sends eligible pages to the existing chunker. Returns immutable decision/chunk tuples in a `ProcessingResult`. Invalid chunk limits raise a fixed `ValueError`. |
| `load_fictional_documents` | Reads a local JSON array. Sanitizes load/parse errors to `ValueError("invalid_fixture")`. Loading alone does not authorize documents. |

Private helpers: `_positive_integer` rejects booleans and nonpositive numbers;
`_parse_date` checks exact date spelling; `_catalog_is_consistent` checks IDs and
replacement chains; `_unique_object` rejects duplicate JSON keys. The nested
`reject_all` helper constructs a batch of fixed rejection decisions.

An `EligibilityDecision` has only `eligible` and `reason`. Reasons are fixed codes:
`valid_metadata` (validation only), `invalid_metadata` (validation only),
`invalid_catalog`, `unsupported_query_mode`, `invalid_reference_date`,
`invalid_permissions`, `access_denied`, `not_approved`, `superseded`,
`not_yet_effective`, or `eligible`.

No rejected title, source, ID, text, or malformed value is copied into decisions.
These are **internal diagnostic results**, not a student-facing API. Even decision
counts/order or reason categories can reveal catalog details if exposed publicly;
a future backend must return a neutral aggregate response without confirming
restricted documents exist. Authorized chunks contain content and must not be
reused across callers or logged indiscriminately.

## Reusing document processing and preserving metadata

`process_documents` calls `split_document_text` once for each eligible page,
passing its real page number, document ID, title, source reference, version, and
the chosen `max_chars`. It uses the returned immutable `DocumentChunk` objects
directly; it does not implement another splitting algorithm.

The existing chunker retains these fields plus chunk text, per-page chunk index,
and normalized-text offsets. Indexes restart on each page; they are not globally
unique persistent IDs. Offsets refer to normalized page text, not PDF coordinates.
Approval/access/effective-date data is used by the eligibility stage but is not
added to PR #8's result type. Revalidation will require looking up authoritative
document metadata later. Existing code and its 19 tests remain unchanged.

## Run the offline example

From the repository root, open Python with `python -B`, then run:

```python
from datetime import date
from ai.document_eligibility import load_fictional_documents, process_documents

documents = load_fictional_documents("tests/fixtures/fictional_documents.json")
result = process_documents(
    documents,
    trusted_permissions={"public"},
    reference_date=date(2026, 10, 25),
)
print([decision.reason for decision in result.decisions])
print(sorted({chunk.document_id for chunk in result.chunks}))
```

Expected IDs: `[101, 103]`. At the default character limit, three pages produce
three chunks. The following table describes fictional fixtures for developer
review, not a response to a student querying restricted documents:

| ID | Fictional document | Public/student result | Explicit public + staff result |
| --- | --- | --- | --- |
| 101 | Current scholarship guidelines, two pages | Eligible | Eligible |
| 102 | Older scholarship guidelines | Superseded | Superseded |
| 103 | Enrollment procedures | Eligible | Eligible |
| 104 | Draft handbook | Not approved | Not approved |
| 105 | Staff memo | Access denied | Eligible |
| 106 | Revoked announcement | Not approved | Not approved |

## Automated tests

```powershell
python -B -m unittest discover -s tests -v
```

`unittest` finds test methods; `-v` prints their names; `-B` avoids bytecode cache
files. [Eligibility tests](../tests/test_document_eligibility.py) exercise approval,
permissions, explicit dates, malformed records, safe decisions, historical denial,
replacement chains, deterministic behavior, JSON errors, and metadata preservation.
A spy wraps the actual chunker and confirms that only eligible page text reaches
it. Another test verifies that a malformed final record causes zero chunker calls,
so earlier pages are not processed before the whole catalog is checked.

The suite uses only Python's standard library and local fictional files. No API
keys, paid model calls, database, or Pinecone are needed. Passing tests demonstrates
these defined cases, not production security or correct answers to arbitrary
natural-language questions.

## Adviser guardrails contribution and remaining work

Implemented: an approval/access/version/date eligibility gate before chunking,
fail-closed malformed input handling, safe rejection structures, preserved source
metadata, and deterministic tests. This demonstrates why apparently relevant text
must be checked before it is used.

Planned minimum viable AI flow:

```text
Backend identity + approved source records -> extraction -> eligibility -> chunks
  -> embeddings -> Pinecone candidate search -> authoritative revalidation
  -> evidence sufficiency/conflict checks -> constrained LLM synthesis
  -> citation/output/privacy validation -> verified answer or safe fallback
```

Embeddings represent text as numbers for similarity search; Pinecone would store
and search those vectors. Neither proves approval, permissions, or factual support.
Future retrieval must revalidate IDs and metadata before exposing text, and again
before answer release if access changes. A real citation must both identify allowed
evidence and support the claim. None of those future stages is implemented here.

Other limitations: no file extraction, upload limits, production auth, semantic
verification, contradiction detection, malicious-document instruction defense,
student-question validator, PII detection, redacted logging service, live revocation,
or cache invalidation. The fictional marker cannot detect real sensitive data.
Source references are local labels, not validated external links. No backend,
frontend, CI, dependency, or database changes are included.

## Decisions Brian and the team must approve

- Map fixture-only status/access/version vocabulary to authoritative database rules.
- Decide whether each immutable version has its own ID and how policy families,
  approval, supersession, revocation, validity intervals, and historical queries work.
- Supply trusted permission grants from server identity; settle public/staff and
  department scopes without trusting client fields.
- Decide whether conservative replacement blocking and whole-catalog rejection fit
  production needs; define transaction/snapshot consistency and source provenance.
- Agree source storage, page numbering, safe citation links, and persistent chunk IDs.
- Design neutral student-facing errors and prevent restricted metadata disclosure.

Cassie should separately integrate offline tests into CI and manage production
secrets. The existing credential concern recorded in the status report is outside
these four files; no production services are used here.

Recommended next small task after review: agree a request-local evidence/citation
identity contract with Brian, then implement an offline citation-membership
validator with fictional tests. It can reject invented IDs and altered metadata
without an LLM, while clearly documenting that membership alone is not factual
support verification.
