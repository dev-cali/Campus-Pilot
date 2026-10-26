# Sprint 3 local RAG MVP — implementation progress

## Current phase: isolated fictional SQLite storage

The S3-02 branch depends on S3-01. Do not imply that S3-01 is merged into main.
The shared database models and existing backend endpoints are unchanged.

Implemented code in this phase (execution still requires local verification):

- [Demo store](../ai/demo_store.py): SQLite engine, tables, repeatable fictional
  seeding, and eligibility-checked public chunks.
- [Database tests](../tests/test_demo_store.py): ten tests using temporary SQLite
  files, never Supabase or an LLM.
- A Git ignore rule for `.campuspilot-demo/`, including SQLite sidecar files.

ELI5: this is a separate practice filing cabinet. It does not rearrange the
team's main cabinet. The local file is not encrypted and is for fictional data
only, including fictional staff records; do not put private records into it.

## Why a separate adapter?

The shared Document model requires a department relationship and does not yet
define the fixture access/source/supersession contract. Importing the shared
database module also initializes its configured engine. The demo module never
imports it or reads DATABASE_URL. It constructs only a SQLite file URL.

This adapter deliberately has its own SQLAlchemy metadata and `demo_` tables.
It is NOT a compatible replacement for the production schema or an Alembic
migration. Brian must approve a mapping before any Supabase integration.

| Demo table | Stored data | Relationship |
| --- | --- | --- |
| demo_documents | Primary document ID and complete validated JSON record, including title, pages, version, approval/access, effective date, source and supersession | Parent |
| demo_chunks | Document ID, page, per-page chunk index, text, normalized offsets | Foreign key to demo_documents |

Keeping the full record in JSON avoids inventing a second set of production
columns during the deadline. It trades SQL-level field constraints/querying for
the existing Python contract validation. The relational ID must match the JSON
ID. SQLite foreign-key enforcement is explicitly enabled on each connection.
Citation metadata is resolved through the parent record, not invented by a model.

## Seeding and retrieval boundary

`seed` first validates/prepares the complete fixture using S3-01 and public-only
permissions. Invalid input fails before database writes. Within one transaction,
it replaces this demo's catalog and prepared chunks. Repeating seeding produces
no duplicates; removed fixture records and obsolete chunks do not linger.
Only this isolated demo catalog is replaced, not any shared application table.

All six valid fictional records are stored for approval/version checks. Only
eligible public pages have prepared chunks. Supersession checks need the complete
catalog, including records not eligible for a student.

`public_chunks` reads current records and reuses S3-01 to regenerate the tiny
public corpus. It does not trust the stored chunk snapshot, which could be stale
after a metadata change or a different reference date. This is inexpensive for
six documents. Production indexing/caching and concurrent revocation handling
need a separate design. The internal complete catalog must never be exposed by
a public API. No client-supplied permission set is accepted by this method.

## Manual verification

From the repository root, using the existing project environment:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Expected after adding this phase: 54 tests (44 existing plus 10 database tests).
This is an expected count, not a claim that the new tests have passed.
Stop on a failure and inspect it before seeding or proceeding.

Verify the local database path is ignored before creating it:

```powershell
git check-ignore .campuspilot-demo/fictional.sqlite3
.\.venv\Scripts\python.exe -B -m ai.demo_store --reference-date 2026-10-26
git status --short --untracked-files=all
```

Expected seed result for the unchanged fixtures: 6 documents and 3 public chunks
(document 101 pages 1/2 and document 103 page 1). Running the seed command twice
should print the same counts. The file stays local and must not be committed.

The reference date is explicit for repeatability. It is not historical-policy
selection; S3-01 still rejects historical query mode. Source references remain
fictional labels, not real university URLs.

## Temporary keyword retrieval phase

[local_retrieval.py](../ai/local_retrieval.py) implements a small `Retriever`
interface, `Evidence` results, and a `KeywordRetriever`. It validates a nonblank
question of at most 2,000 characters, reads fresh eligible public chunks through
`DemoStore.public_chunks`, and ranks candidates by distinct matching words in
their titles/text. Generic words are ignored. Ties use document/page/chunk order.
It returns at most three passages by default, with request-local IDs e1, e2, etc.
Those IDs are not persistent database identifiers and must not be reused across
requests. The 2,000-character limit is a prototype choice for Brian to approve.

Eight new [retrieval tests](../tests/test_local_retrieval.py) cover source metadata,
no matches, exclusion of unsuitable sources, revocation, deterministic limits,
invalid requests, and storage failures. Expected full suite count is now 62.
These new tests have not yet been executed by the assistant. The user supplied
a successful 54-test run for the preceding storage phase.

ELI5: the librarian finds approved reading cards containing words from the
question. Finding the same word does not mean the card answers the question.

This is NOT vector/Pinecone retrieval or evidence sufficiency verification. A GPA
question mentioning scholarships may retrieve scholarship passages even though
they contain no GPA. The answer service must not invent that missing fact.
Similarly, an old-policy question might retrieve a current passage: historical
intent needs an explicit service-level decision before synthesis. This retriever
does not classify historical intent or detect prompt injection.

No match returns an empty tuple. Storage failures remain errors for the future
service to convert to `unavailable`; they are not silently labeled no evidence.
The source interface promises eligible public chunks, but Python type hints alone
cannot enforce authorization. Future adapters must revalidate authoritative data.

After seeding, an optional local developer demonstration is:

```python
from datetime import date
from ai.demo_store import DemoStore
from ai.local_retrieval import KeywordRetriever

store = DemoStore()
try:
    evidence = KeywordRetriever(store).retrieve(
        "Explain the scholarship practice form", reference_date=date(2026, 10, 26)
    )
    print([(e.evidence_id, e.chunk.document_id, e.chunk.page_no) for e in evidence])
finally:
    store.close()
```

This is developer output for fictional data, not a public API response.

## Answering service and FastAPI phase — code added, execution pending

The user verified 62 tests and two successful persistent seed runs (6 documents,
3 public chunks) before this phase. New files:

- [answer_service.py](../ai/answer_service.py): typed response models, excerpt and
  citation validation, conservative scope/absence checks, and orchestration.
- [llm_client.py](../ai/llm_client.py): real OpenAI SDK adapter, lazy configuration,
  JSON-schema output, 20-second SDK timeout and no automatic retries.
- [demo_api.py](../ai/demo_api.py): standalone FastAPI app and POST `/api/ai/ask`.
- [API tests](../tests/test_answer_api.py) and [provider adapter tests](../tests/test_llm_client.py).
- [Evaluation cases](../tests/fixtures/ai_eval_cases.json): 14 fictional question
  cases, expected decisions, allowed source IDs, and simulated provider behavior.
- [Demo requirements](../requirements-demo.txt): pins the six versions reported
  installed in the user's environment; not a full transitive lockfile.

Expected suite count: 71 test methods (62 previous + 9 new). The evaluation cases
run as 14 subtests inside one method. This count is not a claim of a passing run.
Tests inject a mock generator, and SDK tests patch OpenAI construction itself;
real environment keys cannot turn those adapter tests into paid API calls.

### Narrow answer contract

The LLM returns a status plus selected evidence IDs and exact excerpts. The
backend rejects extra fields, empty answers, duplicates, unknown citations,
nonmatching quotes, oversized output, and inconsistent fallback selections.
It then constructs the answer from checked excerpts and source metadata. The
model never supplies source URLs, titles, or document IDs for the final citations.
Answers are explicitly labeled fictional and include `fictional: true`.

This is a real model-assisted **extractive** answer workflow when the live adapter
is configured: the model chooses passages/excerpts; the backend formats them.
It is not a free-form paraphrasing chatbot and no canned successful answer is
substituted for an unavailable model. Confirm that this narrow demonstration meets
the adviser's expectations. Selection quality still needs live evaluation.

Exact quotation prevents invented wording but NOT misleading selection,
incomplete context, or irrelevant answers. A limitation test explicitly demonstrates
that a genuine quotation can pass membership checks without answering a question.
No semantic entailment/conflict detector is claimed. The prompt asks the model to
fall back for insufficient, conflicting, or ambiguous evidence; this instruction
is not a verified security guarantee.

After generation, the service retrieves again and blocks an answered response if
the evidence changed. This reduces stale-release risk but is not transactional
production revocation enforcement. The injected reference date remains fixed
during a request. HTTP requests use the server's current UTC date; tests inject
a fixed date. No date or permission field is accepted from the client.

### Scope and errors

The demo is public-only. Explicit staff/private/secret/password words produce a
neutral denial. Historical/older/previous/superseded words produce an evidence
fallback. These simple signals can miss synonyms and reject benign discussion;
they are not authentication or comprehensive intent/injection detection.
The source eligibility gate, not these words, enforces public document exclusion.

A narrow missing-term check blocks GPA/deadline/fee/amount questions when that
term is absent from passages. Presence of a term does not prove support, and this
check does not understand negation, synonyms, or all multi-part questions.
User questions and passages are sent as untrusted data under a system instruction;
the model has no tools. Broader injection/privacy protections remain future work.

Responses: `answered` and `insufficient_evidence` use HTTP 200, `denied` uses 403,
and `unavailable` uses 503. Invalid request JSON/types/fields use a neutral 422.
No raw validation input, exception text, or rejected model draft is returned.
There is no streaming. The demo has a character limit, not a transport-level
body-size/rate/concurrency limit; bind to loopback and do not deploy publicly.

### Start the local backend without touching Supabase

After all tests pass and the demo has been seeded, run:

```powershell
.\.venv\Scripts\python.exe -B -m uvicorn ai.demo_api:app --host 127.0.0.1 --port 8001
```

Open `http://127.0.0.1:8001/docs`. The existing application and its database module
are not imported. This is a separate demo entry point, not integration into the
shared deployed application. Coordinate mounting the endpoint with Brian later.
No automatic seeding occurs on application startup.

Example POST body:

```json
{"question": "What do fictional learners review for enrollment?"}
```

Without provider configuration, a supported question returns `unavailable`.
A no-evidence question can still return `insufficient_evidence` without a model.
This is honest failure behavior, not a demonstration of live answer generation.

### Offline demonstration

Run the complete test command to exercise temporary SQLite -> retrieval -> mocked
LLM -> backend validation -> HTTP response. The 14 evaluation scenarios include
supported questions, no evidence, draft/revoked sources, historical sources, restricted requests,
ambiguous evidence, injection attempts, invented citations, malformed responses,
timeouts, provider errors, and missing GPA evidence. These are deterministic
acceptance checks of programmed mock behavior, not measurements of a real LLM's
resistance to injection or its answer quality.

### Real AI demonstration — not yet verified

Use the existing project variable `AI_API_KEY`, plus an explicit `AI_MODEL` naming
an account-accessible model that supports Chat Completions JSON-schema output.
No default model or price is assumed. Configure them locally without pasting key
values into chat or committing them. The adapter reads process environment only;
it does not automatically load `.env`. Restart the server after configuration.

The provider uses the existing OpenAI SDK, no additional AI framework. A missing
key/model, model incompatibility, refusal, truncation, timeout, or provider error
produces neutral `unavailable`. The SDK timeout is not a guaranteed total wall-clock
deadline. `store=False` is requested; it is not a promise of zero provider retention.
Do not send private student information in this fictional demo.

Only call this demonstration successful after a real request returns `answered`
with checked excerpts and citations. Record the selected model, date, test question,
and reviewed answer without credentials. Model availability, account access,
cost, and semantic quality still require verification.

### CI and frontend approval boundary

With Marc's explicit approval on behalf of Cassie, CI now includes an additional
step in the existing build-and-check job, after backend dependency installation:

```yaml
- name: Test offline AI workflow
  run: |
    python -m pip install -r requirements-demo.txt
    python -B -m unittest discover -s tests -v
```

The existing Python 3.11 setup, Node.js 20 configuration, frontend installation/build,
backend dependency installation, triggers, permissions, and secrets are unchanged.
The added step installs the demo manifest and runs unittest from the repository
root. A failed install or test command fails the job; no continue-on-error is used.
No AI_API_KEY or external service credentials are required by the tests.
A successful local run does not satisfy the requirement for mocked tests actually
running in GitHub Actions. That requires a later authorized push/PR and a passing run.
The unchanged trigger covers PRs targeting main only: a stacked PR targeting the
S3-01 feature branch will not trigger this workflow. Resolve that sequencing with
Cassie before claiming CI completion; do not silently broaden the trigger.
Josiah/John Paul must integrate the agreed answer/citation contract into the existing
frontend; no duplicate UI or permissive CORS configuration is added here.

## Remaining MVP work

### User-supplied verification on 2026-10-26

The reported database diagnostic found the expected local SQLite file, six stored
documents, three prepared chunks, and a catalog identical to the JSON fixture.
Eligible public document IDs were 101 and 103. The scholarship GPA question
retrieved document 101 pages 1 and 2, but neither passage contained GPA information.
The insufficient_evidence result is therefore correct; no retrieval relaxation
or invented requirement is warranted. This diagnosis is based on the user's
executed command output, not an assistant terminal run.

The last supplied passing full-suite result remains 62 tests. The new API/SDK tests
and expanded 14-case evaluation need a fresh run. No live provider success or
GitHub Actions success has been verified. CI configuration added locally is not
equivalent to a passing hosted CI check.

1. Run and review the new API/adapter tests; fix any failures before proceeding.
2. Verify one genuine provider request and manually evaluate source support.
3. After separate commit/push approval, verify a GitHub Actions run for a PR targeting main.
4. Coordinate the frontend/shared-backend integration and demonstrate it.
5. Expand semantic checks and live-model evaluation based on observed failures.

Pinecone, semantic evidence verification, real authentication, production privacy,
and Supabase migration remain future work. Citation membership alone does not
prove claim support. The existing fixture contains no GPA requirement; asking for
one must not produce an invented number.

No real LLM call or new end-to-end backend test run has been verified yet.
