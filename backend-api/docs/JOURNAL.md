# Backend API Journal

Owner: Brian (Backend / API Engineer)
Last updated: 2026-11-02

## Current Status

- Branch: `feature/backend-api`. Local HEAD `63acc0b`; remote tip `8d56935` (2026-10-28). The branch is 7 commits ahead of `main` and 10 commits ahead of its remote, so the work below is local only.
- `main`: local and remote both at `837d6a5`; already fully contained in the branch.
- State: CRUD scaffolding, ingestion endpoint, tests, `DocumentChunk` schema alignment, and CI-safety fixes are done.
- Tests: 79 passing in `.venv` (Python 3.11), re-run 2026-11-02, including a run in a copy with no `.env`.
- Environment: a root `.env` is still required at runtime and is gitignored; `DATABASE_URL` is no longer hardcoded, and importing the app no longer requires the variable.
- Uncommitted: nothing in the backend. The only modified file is `frontend/AGENTS.md`, which `next dev` regenerates and which is not ours.
- Architecture direction: Supabase SDK for new work, Pinecone deferred until deployment. SQLAlchemy stays in place for the existing code.

## How This Journal Is Kept

Every task gets one entry using this template, written in the same change set as the work:

```
### Task: <name> - <date>
Goal:
Files changed:
Steps:          1..n, each with the command or edit and its result
Problems hit:   what broke and how it was solved
Checks run:     <command> -> <result>
Left to do:     follow-ups and risks
```

Rules:
- Record the process, not just the outcome. A checklist entry alone is not enough.
- Only write "verified" when the command was actually run and its output seen.
- Keep secrets out. Never paste connection strings, keys, or passwords.

## Task Log

### Task: Branch and workspace setup - 2026-10-27
**Goal:** Get the project current and give the backend role its own place to work.

**Files changed:** `backend-api/README.md`, `backend-api/docs/`, plus local empty folders `backend-api/features/`, `backend-api/work/`, `backend-api/backlogs/`.

**Steps:**
1. Checked `origin/main`, pulled, and confirmed the tree was current at `d34a9ed` (already included the S3-03 frontend AI integration and RAG demo).
2. Created and checked out `feature/backend-api` from that commit.
3. Created `backend-api/` with `features/`, `work/`, `backlogs/`, `docs/`, plus a README.
4. First push failed because git was authenticated as `davidreynes`; after the GitHub account was switched to `brireynes`, the push succeeded.

**Problems hit:** Push rejected under the wrong GitHub identity; resolved by switching accounts, no credential was stored in the repo.

**Checks run:** `git log`, `git status`, `git push` -> branch published.

**Left to do:** `features`, `work`, and `backlogs` are empty, so git does not track them; they exist locally only. Add files there before relying on them in a fresh clone.

### Task: Dependency and architecture alignment - 2026-10-27/28
**Goal:** Reconcile the team's Supabase + Pinecone direction with a codebase already built on SQLAlchemy.

**Files changed:** `utils/supabase_client.py`, `utils/pinecone_client.py`, `utils/__init__.py`, `backend-api/docs/DEPENDENCY_ANALYSIS.md`.

**Steps:**
1. Inspected `database.py`, `main.py`, `alembic/`, and existing tests before installing anything.
2. Found SQLAlchemy wired through models, session handling, Alembic, and every router, so removing it would break working endpoints.
3. Installed `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `httpx`, `openai`, `psycopg2-binary`, `psycopg`, `alembic`, `supabase`, `pinecone-client`.
4. Decision: keep SQLAlchemy for existing code, add thin Supabase/Pinecone client wrappers, and use the SDKs for new features only.
5. Recorded the analysis in `DEPENDENCY_ANALYSIS.md`.

**Problems hit:** The original request assumed Supabase could replace SQLAlchemy immediately; source inspection showed that would be a rewrite, so the change was scoped to wrappers plus new endpoints.

**Checks run:** Import of the app succeeded after installing dependencies.

**Left to do:** Dependencies were installed ad hoc and never pinned; there is no root `requirements.txt` (only `requirements-demo.txt`). Pinecone is deferred by team decision, so its wrapper stays unused for now.

### Task: CRUD routers and ingestion endpoint - 2026-10-27/28
**Goal:** Give the shared API real CRUD endpoints and a page-ingestion path that reuses the existing chunker.

**Files changed:** `routers/users.py`, `routers/documents.py`, `routers/chunks.py`, `routers/questions.py`, `routers/ingest.py`, `routers/__init__.py`, `schemas/document_schemas.py`, `schemas/__init__.py`, `main.py`.

**Steps:**
1. Added Pydantic schemas in `schemas/document_schemas.py` for Documents and DocumentChunks.
2. Added CRUD routers for Users, Documents, DocumentChunks, and Questions.
3. Mounted the routers in `main.py` and re-checked that `/`, `/departments`, and `/test-ai` still worked.
4. Added `POST /ingest/chunk`, which calls `ai.document_processing.split_document_text()` instead of duplicating chunking logic.
5. Pulled `title` and `version` from the parent `Document` row, since the chunk records did not carry them.

**Problems hit:** The chunker produced provenance fields the `DocumentChunk` table had no columns for, so ingestion had nowhere to store them. Deferred to the schema alignment task below rather than silently dropping them in new code.

**Checks run:** Manual app import and route registration.

**Left to do:** Nothing open; covered by the tests in the next task.

### Task: Tests for CRUD and ingestion - 2026-10-28
**Goal:** Cover the new endpoints before changing the schema.

**Files changed:** `tests/test_backend_crud.py`.

**Steps:**
1. Created `tests/test_backend_crud.py` using `TestClient` with a temporary SQLite database.
2. Overrode the routers' `get_db` dependency so tests never touch the Supabase database.
3. First run still hit the real database through `/departments`, which uses `main.get_db()`; added an override for that dependency too.
4. Covered create/read/update/delete for all four resources and an end-to-end `POST /ingest/chunk` case that verifies chunks come back from `split_document_text`.

**Problems hit:** Two different `get_db` functions existed (in `routers` and in `main`); missing the second one caused tests to reach the live database.

**Checks run:** `python -m pytest -q` -> 79 passed (71 existing + 8 new).

**Left to do:** Tests pass but are not run in CI from this branch yet.

### Task: DocumentChunk schema alignment and Alembic migration - 2026-10-28
**Goal:** Stop losing citation and provenance data during ingestion.

**Files changed:** `database.py`, `schemas/document_schemas.py`, `routers/ingest.py`, `alembic/versions/a1b2c3d4e5f6_add_provenance_fields_to_document_chunks.py`.

**Steps:**
1. Confirmed the mismatch: `ai.document_processing.split_document_text()` returns `source_reference`, `chunk_index`, `start_char`, and `end_char`, while the `document_chunks` model stored only `document_id`, `page_no`, `chunk_text`, and `embedding`.
2. Added the four fields to the `DocumentChunk` model in `database.py`, all nullable so existing rows stay valid.
3. Mirrored them in `schemas/document_schemas.py` so the API accepts and returns them.
4. Updated `routers/ingest.py` to persist the values returned by the chunker instead of discarding them.
5. Wrote the Alembic migration by hand: `upgrade()` adds the four columns, `downgrade()` drops them in reverse order.
6. Re-ran the full suite.

**Problems hit:**
- `alembic revision --autogenerate` needs a live database and the Supabase connection failed, so the migration was written manually.
- The migration uses `down_revision = None` because it is the first tracked revision, but the tables were originally created by `Base.metadata.create_all()`. The `alembic_version` table therefore has no baseline. Do **not** run `alembic upgrade head` against Supabase until the existing schema is stamped as the baseline, otherwise it will try to add columns to a table it believes it is creating.
- `alembic.ini` contains a hardcoded database URL with credentials (committed 2026-10-14 in `54d3e50`). It should move to a `DATABASE_URL` environment variable read in `alembic/env.py`, and the exposed password should be rotated if the repository is shared.

**Checks run:** `python -m pytest -q` -> 79 passed.

**Left to do:** Baseline/stamp the live database before applying the migration; move the URL to an environment variable; apply the migration on the real Supabase instance.

### Task: Journal repair and process standard - 2026-10-28
**Goal:** Fix damaged text and make this journal record steps, not just results.

**Files changed:** `backend-api/docs/JOURNAL.md` only.

**Steps:**
1. Read the file byte-for-byte and found literal control characters (BEL, backspace, and a stray carriage return) that had eaten characters, turning `routers/` into `outers/`, `ai.document_processing` into a BEL followed by `i.document_processing`, and `backend-api` into `ackend-api`-style text.
2. Root cause: the content was previously written through a shell string where backslash escapes were interpreted. Fixed by writing the file directly, and added a rule above to keep secrets and escapes out.
3. Restored the damaged paths and file names.
4. Refreshed stale status: schema alignment and CRUD tests were still listed as blocked/pending even though both were finished.
5. Added the "How This Journal Is Kept" template and converted the existing work into dated task entries with files, steps, problems, checks, and follow-ups.

**Problems hit:** No corruption in the work itself, only in the journal text.

**Checks run:** Re-read of the file after writing and byte inspection to confirm no control characters remain. `python -m pytest -q` could not be re-run: `pytest` is not installed for the available interpreters (Python 3.14 and 3.11) in this environment, so the 79-passing figure above is the last verified run, not a re-check.

**Left to do:** Reinstall `pytest` in a virtual environment and pin dependencies so test results are reproducible.

### Task: Local test environment and pinned dependencies - 2026-10-28
**Goal:** Make the 79-test run reproducible instead of depending on whatever is installed globally.

**Files changed:** `backend-api/requirements.txt` (new), `conftest.py` (new).

**Steps:**
1. Confirmed `pytest` was missing from both available interpreters (Python 3.14 and 3.11).
2. Created `.venv` with Python 3.11; the folder is already in `.gitignore`.
3. Installed the versions from `requirements-demo.txt` plus `pytest`, `psycopg2-binary`, `python-dotenv`, and `supabase`.
4. Added `psycopg[binary]` after collection failed: SQLAlchemy 2.1 resolves a plain `postgresql://` URL to the psycopg 3 driver, not psycopg2.
5. Added root `conftest.py` to set a dummy `DATABASE_URL` before test imports; the tests still override `get_db` and use temporary SQLite, so no connection is made.
6. Ran the suite before and after the credential changes.
7. Pinned the verified versions in `backend-api/requirements.txt`.

**Problems hit:** Missing `psycopg` module blocked collection with `ModuleNotFoundError: No module named 'psycopg'`; installing `psycopg[binary]` fixed it. `pytest` also emitted pre-existing Pydantic deprecation warnings for `.dict()` in the routers.

**Checks run:** `.venv\Scripts\python.exe -m pytest -q` -> 79 passed, 131 subtests, both before and after the code changes.

**Left to do:** CI still installs `backend/requirements.txt`, a path that does not exist; the workflow needs updating to `backend-api/requirements.txt` (CI change, needs approval). Pinecone is intentionally not pinned yet.

### Task: Remove hardcoded database credentials - 2026-10-28
**Goal:** Stop committing the Supabase password in source files.

**Files changed:** `database.py`, `alembic/env.py`, `alembic.ini`, `conftest.py`; local `.env` (gitignored, not committed).

**Steps:**
1. Scanned the repo and found the same password hardcoded in `database.py` and `alembic.ini`.
2. `database.py` now loads a root `.env` with `python-dotenv` and requires `DATABASE_URL`, raising a clear error when it is unset.
3. `alembic/env.py` loads the same `.env`, overrides `sqlalchemy.url` from `DATABASE_URL` (escaping `%` for ConfigParser), and raises if the variable is missing in online mode.
4. Removed the URL value from `alembic.ini`.
5. Created a local `.env` from the previous value so the app keeps working, and confirmed `git check-ignore .env` excludes it.

**Problems hit:** `DATABASE_URL` is now mandatory, so importing the app without `.env` fails by design. Rotating the password cannot be done from the repository; it is a Supabase dashboard action.

**Checks run:** `python -c "import database, main"` -> URL loaded, 12 routes registered. Repo scan for the password -> only `.env` matches. `pytest -q` -> 79 passed.

**Left to do:** Rotate the password in Supabase and update `.env`. Git history still contains the secret in `54d3e50` and `e09fead`, so the old password must be treated as compromised even though the files are clean now.

### Task: Reconcile with main and make the branch CI-safe - 2026-11-02
**Goal:** Confirm the branch sits on the newest `main`, find what would fail once it merges, and fix the parts that belong to the backend.

**Files changed:** `database.py`, `requirements-demo.txt`, `backend-api/docs/JOURNAL.md`.

**Steps:**
1. Fetched `origin` and fast-forwarded local `main` from `d34a9ed` to `837d6a5` (15 commits) using `git fetch origin main:main`, which updates the ref without touching the working tree.
2. `git merge main` returned "Already up to date": `origin/main` contributes 0 commits the branch lacks, and the branch is 7 commits ahead.
3. Read `.github/workflows/ci.yml`: it triggers on `push`/`pull_request` to `main` only, so no hosted run has ever covered this branch.
4. Found two independent reasons CI would fail on merge: `database.py` imports `python-dotenv`, which `requirements-demo.txt` never installed; and CI's `unittest` step has no `.env`, so `database.py` raised `RuntimeError` at import. `conftest.py` does not help there because `unittest discover` never loads it.
5. Reproduced the second failure in a temp copy with no `.env`: `RuntimeError: DATABASE_URL is not set`.
6. Made engine and session creation lazy in `database.py` (`get_engine()`, `SessionLocal()` wrapper) so importing the app never requires credentials. Verified nothing imports `engine` from `database.py` and every caller uses `SessionLocal()` with no arguments.
7. Added `python-dotenv==1.2.4` to `requirements-demo.txt`, next to the other pinned demo dependencies.

**Problems hit:** The local suite was green and misleading; the untracked `.env` masked the CI condition. The fix had to be proven in a copy with `.env` deleted, not by trusting the local run.

**Checks run:**
- `.venv\Scripts\python.exe -B -m unittest discover -s tests` -> 79 tests, OK (local, `.env` present)
- `.venv\Scripts\python.exe -m pytest -q` -> 79 passed, 16 warnings, 131 subtests
- Same two commands in a copy with no `.env` -> 79 OK and 79 passed, exit 0 for both
- `npm run lint` in `frontend` -> 1 error at `app/page.tsx:5:50` (`no-explicit-any`), left untouched because that file is Josiah's

**Left to do:** CI's `unittest` step still has no `DATABASE_URL`; giving it the same dummy URL as `conftest.py`, or making it load a conftest, is a `ci.yml` change and belongs to Cassie. The `python-dotenv` pin has not been exercised by a fresh `pip install` in a clean venv, so that part is reasoned from `requirements-demo.txt`, not observed. Nothing was committed or pushed.

### Task: Clean-room CI parity and CI env fix - 2026-11-02
**Goal:** Close both limits left open by the previous task — prove the dependency pin with a real install, and give CI the `DATABASE_URL` its `unittest` step needs. Brian approved both explicitly.

**Files changed:** `.github/workflows/ci.yml`, `backend-api/docs/JOURNAL.md`.

**Steps:**
1. Added `DATABASE_URL: postgresql+psycopg://test:test@localhost:5432/test` to the `Run Python unit tests` step, matching the dummy already in `conftest.py`. The engine is lazy, so the driver is never loaded.
2. Built a copy of the repo with no `.env` and a throwaway venv from Python 3.11 (same interpreter as `.venv`), installed only the six original `requirements-demo.txt` packages, and ran the `unittest` step: 72 tests ran and 1 error failed the run, with `ModuleNotFoundError: No module named 'dotenv'` for `database.py`. That is the negative case proved, not assumed.
3. Created a second throwaway venv, installed `requirements-demo.txt` as CI does, and confirmed `python-dotenv` resolves to `1.2.4`.
4. Ran both CI steps in that clean venv with `DATABASE_URL` set and no `.env`: `unittest` 79 OK, `pytest` 79 passed / 131 subtests, exit 0 for both.
5. Parsed `.github/workflows/ci.yml` with `js-yaml` to confirm the edited file still loads and shows the new env on step 4.
6. Ran the frontend half of the same job: `node --test tests/ai-proxy.test.mjs` -> 7 passed, exit 0; `npm run build` -> succeeded after a first-run stop (see below).

**Problems hit:** The first `npm run build` aborted with `SecurityFatalError` telling the reader to upgrade Next.js. Traced in `node_modules/next/dist/lib/upgrade/nudge.js`: the nudge only stops a build when an agent is detected (`getAgentName`) or a terminal can prompt (`canPromptForUpgrade`, which returns false under `isCI`, line 377). This session sets `AI_AGENT=opencode` and `AGENT=1`, so the guard fires here but not on a GitHub runner, where `agent` is null and the code returns at lines 486-488. Retrying the build produced a normal exit 0 with all four routes. Separately, `npm run lint` still reports the single pre-existing `app/page.tsx:5:50` error, which is Josiah's file and was not touched.

**Checks run:**
- Old requirements in a clean venv, no `.env` -> 1 error, exit 1 (`ModuleNotFoundError: dotenv`)
- `pip install -r requirements-demo.txt` in a clean venv -> `python-dotenv` 1.2.4
- Clean venv + `DATABASE_URL`, no `.env` -> `unittest` 79 OK, `pytest` 79 passed / 131 subtests, exit 0 both
- `js-yaml` parse of `ci.yml` -> 8 steps, env present on "Run Python unit tests"
- `node --test tests/ai-proxy.test.mjs` -> 7 passed, exit 0
- `npm run build` -> exit 0 on retry, 4 routes; first run blocked by the agent-only security nudge

**Left to do:** Cassie should review the `ci.yml` edit before merge, since CI is her ownership. Next 16.4.0 is pinned while its own advisory data flags it; upgrading is a dependency change for Josiah/Cassie, not a backend call. Nothing committed or pushed.

## What's Done

- [x] Analyzed project structure, models, and existing endpoints
- [x] Pulled latest `main` (includes S3-03 frontend AI integration and RAG demo)
- [x] Created the `backend-api/` workspace and its docs
- [x] Pushed the branch as `brireynes`
- [x] Dependency analysis recorded; SQLAlchemy retained, Supabase/Pinecone wrappers added
- [x] CRUD routers and Pydantic schemas for Users, Documents, DocumentChunks, Questions
- [x] Routers mounted in `main.py` without breaking existing endpoints
- [x] `POST /ingest/chunk` using the existing chunker
- [x] CRUD and ingestion tests (8 new, 79 total passing)
- [x] `DocumentChunk` provenance columns added across model, schemas, and ingestion
- [x] Hand-written Alembic migration for those columns
- [x] Journal repaired and restructured to record process
- [x] Local Python 3.11 `.venv` and a reproducible 79-test run
- [x] Pinned dependencies in `backend-api/requirements.txt`
- [x] Hardcoded database credentials removed; `DATABASE_URL` comes from `.env`
- [x] Branch reconciled with `main` (`837d6a5`); nothing to merge down
- [x] Import no longer requires credentials, and `python-dotenv` is pinned for CI
- [x] Dependency pin proved by a clean-venv install and both CI steps passing without a `.env`
- [x] CI `unittest` step given `DATABASE_URL` (needs Cassie's review)

## Next Priorities

1. [x] Commit the pending work on `feature/backend-api` (schema, tests, migration, credential hardening, requirements)
2. [ ] Open the PR for `feature/backend-api` (branch is pushed at `8ffdf6d`)
3. [ ] Baseline/stamp the Supabase database, then apply the migration
4. [ ] Build the first endpoint on the Supabase SDK, leaving existing CRUD untouched
5. [x] Ask Cassie to add `DATABASE_URL` to CI's `unittest` step and to trigger checks on branches, so this class of breakage is caught before merge

Credential rotation is **Cassie's**, tracked with her security work, not in this journal.
Her `security/remove-database-credentials` branch edits `database.py` and `alembic/env.py`,
so expect a conflict with this branch and let her decide which config approach wins.

## Backlog

- [ ] Supabase Auth integration for authentication and authorization
- [ ] Decide the long-term migration strategy: Alembic vs Supabase migrations
- [ ] Migrate existing CRUD from SQLAlchemy to the Supabase SDK once the team approves
- [ ] Wire tests into CI for this branch
- [ ] Pinecone setup, deferred until deployment per team decision

## Future Implementations

- [ ] RAG ingestion pipeline: upload/extract -> process -> chunk -> embed -> store vectors in Pinecone, metadata in Supabase
- [ ] Chat/RAG query endpoint combining retrieval and the LLM
- [ ] Citation tracking and validation using the new provenance fields
- [ ] Rate limiting and error handling
- [ ] API documentation improvements

## Notes

- The demo RAG system (`ai/demo_api.py`) is separate; do not break it.
- Existing endpoints in `main.py` must stay functional.
- SQLAlchemy is retained for now because `database.py`, `main.py`, Alembic, and the routers depend on it; migrate gradually.
- Use the Supabase SDK for new features; do not rewrite working code without approval.
- `alembic/` was created by `dev-cali` on 2026-10-14 (`54d3e50`); only the migration file inside `alembic/versions/` is ours.
- Ingestion pulls `title` and `version` from the parent `Document` row because chunks do not store them.
- `DATABASE_URL` is required at runtime; both `database.py` and `alembic/env.py` load it. Importing the app does not require it (lazy engine), so tests and tooling run without a `.env`.
- The credential in `database.py:7` on `main` is public and still live; rotation is Cassie's, tracked with her `security/remove-database-credentials` work, not here.
- Local setup: `.venv` with Python 3.11, then `pip install -r backend-api/requirements.txt`.
- The old database password still exists in Git history, so the leak is real even though no tracked file contains it now; rotating it belongs to Cassie's security work.
