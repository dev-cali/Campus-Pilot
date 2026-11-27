# Final Technical Documentation

**Project / course section:** CampusPilot / CSP221A — [COURSE SECTION REQUIRED]\\
**Team:** Marc — AI Engineering; Brian — Backend/API; Cassie — DevOps Engineer (sole designated DevOps Engineer); Josiah — Frontend; John Paul — Full-stack / department integration\\
**Evidence baseline:** `origin/main` commit `c457c2c69ac59b5c8495e9d5c509222fa6b7343f` (PR #44, 27 Nov 2026). Production deployment SHA: [PRODUCTION SHA UNVERIFIED]. No release tag was found in fetched repository tags.\\
**Links:** [Repository](https://github.com/dev-cali/Campus-Pilot) · [Production site](https://campus-pilot-kappa.vercel.app) · [AI assistant](https://campus-pilot-kappa.vercel.app/ai) · [AI API docs](https://campuspilot-ai-demo.onrender.com/docs)

## 1 Product status & architecture

CampusPilot is a university information and student-support portal for learners and staff. The repository contains a department/document/question API and a separate fictional-university AI demonstration. The approved pitch and course section were not located. The AI demo answers from fictional Demo Campus University sources; it is not an official university policy system.

**Status:** The portal and authenticated AI question flow are implemented in source. Keyword-grounded RAG and deterministic tuition calculations are covered by offline tests; hosted CI passed for PR #44. Optional Pinecone ingestion/retrieval code is merged, but its authenticated preflight returned HTTP 401; no upload or live semantic retrieval is verified. Current production SHA and latest live checks are unverified. Changes against the approved pitch require team confirmation.

**Runtime:** User → Next.js UI → Supabase session/claims-checked proxy → authenticated FastAPI AI service → eligible fictional SQLite evidence → deterministic calculation or structured OpenAI selection → strict evidence/citation validation → UI. The portal SQLAlchemy database is separate from the fictional SQLite knowledge store. [Architecture diagram required.]

## 2 Technology & dependency disclosure

| Area | Verified implementation |
|---|---|
| Frontend / UX | TypeScript, Next.js 16.4.6, React 19.3.0, Supabase SSR; Vercel. |
| Backend / API | Python/FastAPI 0.162.0, Uvicorn 0.54.0, SQLAlchemy 2.1.6; Render AI service. CI uses Python 3.13; deployed version unverified. |
| Database / auth | Main app PostgreSQL URL configuration; SQLAlchemy and Alembic. Separate SQLite AI demo. Supabase SSR auth. |
| AI / data tools | OpenAI SDK 3.37.0, model gpt-5-mini; keyword retrieval default. Pinecone SDK 10.3.0 optional; schema expects llama-text-embed-v2, 1,024 dimensions, cosine, field `chunk_text`. |
| DevOps / quality | GitHub Actions, pytest, unittest, Node tests, ESLint, Next.js type generation, TypeScript and production build. Latest PR #44 CI and both Vercel checks passed. |
| External / costs | Fictional JSON corpus; OpenAI and Pinecone can incur usage costs. Codex/ChatGPT assisted development; outputs reviewed through source, tests and PR checks. Hosting tiers, costs, asset licenses and full dependency-license inventory unverified. |

Manifests: [frontend package.json](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/frontend/package.json) · [backend requirements](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/requirements-demo.txt) · [environment names only](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/.env.example)

## 3 Data model, API & user workflow

**Relationships:** `departments.id` (PK) 1→many `documents.department_id` (FK); `documents.id` 1→many `document_chunks.document_id`; `users.id` 1→many `questions.user_id`; departments also own questions. SQLite demo: `demo_documents` 1→many `demo_chunks`, keyed by document/page/chunk. Models: [database.py](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/database.py). One Alembic revision adds chunk provenance; complete initial migration history and ERD are unverified: [migration](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/alembic/versions/a1b2c3d4e5f6_add_provenance_fields_to_document_chunks.py), [ERD required].

**Routes:** Next.js `POST /api/ai/ask` verifies Supabase session/claims, validates 1–2,000 characters and forwards server-side credentials. FastAPI `POST /api/ai/ask` validates request, shared secret and quota. Legacy FastAPI routers expose user/document/chunk/question CRUD methods; deployed create/read/update/delete evidence is unavailable. API reference: [Render /docs](https://campuspilot-ai-demo.onrender.com/docs); CI does not prove every route is live.

## 4 AI feature: design, output processing & evidence

RAG supplies relevant passages to a model, enabling flexible questions beyond fixed rules. The fictional catalog has 13 records: 9 eligible public documents, 4 excluded controls and 23 eligible chunks. Eligibility requires approved, public, current and effective records; citations are rebuilt from trusted local records. The model returns a strict evidence selection, not trusted answer text. Backend checks schema, question coverage, exact quotations, IDs and citations; unsupported questions abstain. Tuition totals use deterministic calculation where applicable.

The corpus is fictional, not actual policy. Evidence is capped at 2 chunks and 2,000 characters. [Corpus](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/tests/fixtures/fictional_documents.json) · [retrieval](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/ai/local_retrieval.py) · [validation](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/ai/answer_service.py).

**Evaluation:** Corrected Phase 4.4 post-freeze, non-blind retrieval validation: 22 cases (20 supported), 100% required-evidence coverage and returned-evidence precision, zero excluded leaks; median 17.33 ms, p95 27.59 ms (440 local runs; initialization excluded). Phase 5 mocked evaluation: 40 cases, 34 supported; component layer 34/34 complete, end-to-end 29/34 complete, 5 safe retrieval abstentions, zero unsupported acceptances and citation failures. Offline metrics do not establish live-model accuracy. [Evaluation index](https://github.com/dev-cali/Campus-Pilot/tree/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/docs/evaluation).

**Pinecone:** PR #44 merged optional SDK 10.3.0 Documents API integration. Explicit dry-run/apply ingestion uses a fictional namespace and stable IDs with content digests; evidence is locally revalidated and keyword fallback remains. Recorded schema preflight failed HTTP 401; no records were uploaded and semantic retrieval is unverified. Keep `AI_RETRIEVAL_MODE=keyword_only`.

## 5 Security, data protection & reliability

Secrets remain server-side. Supabase session/claims are checked before proxying; FastAPI separately requires a shared secret and limits requests to 5/minute and 100/day per process. Questions are limited to 2,000 characters; retrieval allows eligible public evidence only. Structured output and citation checks fail closed; errors are sanitized. Timeouts: OpenAI 60 s, proxy 75 s, browser 110 s, Vercel function 120 s; Pinecone 2 s per attempt, 7.5 s overall. Browser cancellation does not guarantee provider cancellation or prevent billing. Configuration names: [.env.example](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/.env.example).

## 6 Testing: report actual counts and results

| Check | Verified result |
|---|---|
| Automated checks | PR #44: 229 Python tests passed, including 17 Pinecone tests; 444 pytest subtests passed. GitHub Actions, both Vercel checks and Preview Comments passed. [CI run](https://github.com/dev-cali/Campus-Pilot/actions/runs/46024481307) |
| AI evaluation | Phase 4.4 and Phase 5 offline results above; mocked provider. [Results](https://github.com/dev-cali/Campus-Pilot/tree/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/docs/evaluation) |
| Production checks | Eight AI scenarios were previously user-reported successful: calendar/class dates, passing grade, transcript, scholarship, multipart, tuition, personal-GPA refusal and restricted-data refusal. Not rerun against PR #44 deployment; current SHA and CRUD smoke evidence unverified. |
| Known defects | Pinecone 401 blocks preflight; no upload/live semantic test. Current hosting cold-start/cost limits and production state not measured. |

## 7 Engineering process & CI/CD

Work uses feature branches and pull requests to `main`. CI runs Python 3.13 unittest/pytest, frontend install, lint, route type generation, TypeScript, proxy/reliability tests and production build. PR #44 merged to `main` at `c457c2c`; hosted workflow and both Vercel checks passed. [Workflow](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/.github/workflows/ci.yml) · [PIPELINE.md](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/PIPELINE.md) · [PR #44](https://github.com/dev-cali/Campus-Pilot/pull/44).

Branch protections, required reviews, Vercel production gating, Render tracking, latest deploy SHA and comparable pipeline duration/success rates were not verified. Rollback steps are documented but untested. [Pipeline metrics required.] [Continuous deployment challenge video required.]

## 8 Contribution and external-work disclosure

Team-assigned roles: Marc—AI Engineering; Brian—Backend/API; Cassie—DevOps Engineer (sole designation); Josiah—Frontend; John Paul—full-stack/department integration. Integration evidence: [PR #40](https://github.com/dev-cali/Campus-Pilot/pull/40), [PR #41](https://github.com/dev-cali/Campus-Pilot/pull/41), [PR #42](https://github.com/dev-cali/Campus-Pilot/pull/42), [PR #43](https://github.com/dev-cali/Campus-Pilot/pull/43), [PR #44](https://github.com/dev-cali/Campus-Pilot/pull/44). PR authorship is not a complete task ledger.

Codex/ChatGPT supported coding and documentation; source inspection, automated tests and PR checks provide review evidence. No new manual production check is claimed. Dependencies and model services are listed above. The course template was supplied locally; confirm its upstream license and UI asset attributions.

## 9 Current limitations and final status

**Implemented:** university portal source, authenticated AI proxy, fictional keyword RAG, evidence/citation validation, deterministic tuition, optional Pinecone integration and automated CI.

**Partial/unverified:** Pinecone auth/ingestion/semantic behavior; production SHA/live checks; deployed legacy CRUD; initial schema migration completeness; branch protections, operational metrics, ERD and challenge recording.

**Next:** resolve Pinecone credentials and run approved isolated preflight, ingestion and semantic tests before enabling it; complete production smoke evidence and reviewer artifacts. Pinecone is optional and not verified operational.

## 10 Reviewer evidence index

| Evidence | Link |
|---|---|
| Product, source, release | [Production](https://campus-pilot-kappa.vercel.app) · [Repository](https://github.com/dev-cali/Campus-Pilot) · [main commit c457c2c](https://github.com/dev-cali/Campus-Pilot/commit/c457c2c69ac59b5c8495e9d5c509222fa6b7343f); no release tag found |
| Technical specs | [README](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/README.md) · [Architecture](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/docs/offline_rag_architecture.md) · [ERD required] · [API docs](https://campuspilot-ai-demo.onrender.com/docs) |
| AI and testing | [Evaluation](https://github.com/dev-cali/Campus-Pilot/tree/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/docs/evaluation) · [CI run](https://github.com/dev-cali/Campus-Pilot/actions/runs/46024481307) · [Error handling](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/ai/answer_service.py) |
| DevOps and process | [CI workflow](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/.github/workflows/ci.yml) · [PIPELINE.md](https://github.com/dev-cali/Campus-Pilot/blob/c457c2c69ac59b5c8495e9d5c509222fa6b7343f/PIPELINE.md) · [PRs](https://github.com/dev-cali/Campus-Pilot/pulls) · [Sprint records required] |
| Deployment video | [Continuous deployment challenge recording required] |

**Manual placeholders:** course section; production deployment SHA; architecture diagram; ERD; deployed CRUD evidence; current deployment settings; pipeline metrics; uninterrupted challenge recording; sprint contribution records; hosting/cost and asset/dependency license attributions.
