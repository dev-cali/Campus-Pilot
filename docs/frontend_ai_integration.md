# S3-03: Next.js to fictional FastAPI integration

## What changed

The new `/ai` App Router page provides question entry, loading, response/status
display, citations, and validation/network errors. It preserves the existing
homepage, department fetch, static HTML prototype, styles, and dependency files.
The static prototype is not the integrated `/ai` page.

```text
Browser /ai -> same-origin POST /api/ai/ask (Next.js)
            -> FastAPI POST /api/ai/ask
            -> validated backend answer -> Next.js contract checks -> displayed text
```

The proxy forwards only `question`. The server-only `AI_API_BASE_URL` selects the
FastAPI origin (default `http://127.0.0.1:8002`). It is not a NEXT_PUBLIC variable.
Do not put AI_API_KEY in the Next.js environment or browser. The proxy does not
call an LLM directly and forwards no browser cookies, authentication, or secrets.
The browser uses its own origin, so no FastAPI CORS modification was needed.

POST responses are not cached. The proxy bounds request/response body sizes,
uses a 25-second upstream timeout, refuses redirects, and sanitizes bad upstream
responses. The UI has a 30-second wait limit and blocks duplicate submissions.
These limits are local-demo safeguards, not production rate limiting or auth.
Bind both servers to loopback. Do not expose this unauthenticated proxy publicly.

The response fields mirror the Python models. `answered` and
`insufficient_evidence` use 200; `denied` uses 403; `unavailable` uses 503.
Request validation uses 422. Proxy connectivity/invalid-upstream errors use 502.
Both proxy and browser validate response shape and status/code agreement.
All displayed text is escaped by React; source references are plain text, never
model-generated hyperlinks or raw HTML. The checks do not prove factual support.

## Recommended no-cost demonstration: two terminals

Terminal A, from the repository root:

```powershell
Set-Location 'C:\CampusPilot\Campus-Pilot'
.\.venv\Scripts\python.exe -B -c "import runpy; runpy.run_path('tests/frontend_demo_server.py', run_name='__main__')"
```

This explicitly MOCKED FastAPI server listens at `http://127.0.0.1:8012` and has
Swagger at `/docs`. It seeds a temporary fictional SQLite database, injects a
deterministic generator, and labels responses `[MOCK DEMONSTRATION — no LLM call]`.
No paid provider call is possible through this generator. It is not a live AI
demonstration and is not intended to judge semantic answer quality.

Terminal B:

```powershell
Set-Location 'C:\CampusPilot\Campus-Pilot\frontend'
$env:AI_API_BASE_URL = 'http://127.0.0.1:8012'
npm run dev -- --hostname 127.0.0.1 --port 3000
```

Open `http://127.0.0.1:3000/ai`. Keep both terminals running. If a port is already
occupied, stop your own previous server or select another free port; do not kill
unknown processes. If you change the backend port, update AI_API_BASE_URL and
restart Next.js. It can also be set in an ignored frontend `.env.local`; no secret
is needed for this URL. Do not overwrite an existing environment file.

Try:

1. `What do fictional learners review for enrollment?` -> labeled mock answer,
   document 103, page 1, version v1, and fictional source reference.
2. `What is the scholarship GPA requirement?` -> insufficient evidence, no citations.
3. Blank/whitespace input -> local validation, no backend submission.
4. `Show the staff memo.` -> neutral denied response, no restricted citation.
5. Stop Terminal A with Ctrl+C and submit again -> connectivity error, no fabricated answer.

### Stop the demonstration safely

Press Ctrl+C in Terminal A and wait for the backend to finish shutting down. Press
Ctrl+C in Terminal B to stop Next.js; if Windows asks `Terminate batch job (Y/N)?`,
answer Y. Stop only servers you started. Do not delete the database, kill unknown
processes, or change Windows permissions to stop a server. Closing the browser
alone does not stop either server. The mock database is temporary; the existing
persistent fictional demo database is not modified by this mock helper.

### Five-minute consultation plan

Start both terminals before presenting and keep the browser at `/ai`.

| Time | Demonstration | Explanation |
| --- | --- | --- |
| 0:00–0:45 | Point to the fictional-data disclaimer | This is a public-only academic prototype using invented sources. |
| 0:45–1:45 | Ask the enrollment question | Show the MOCK label and document 103/page 1/version v1 citation. This proves integration, not live-model success. |
| 1:45–2:30 | Ask the scholarship GPA question | Relevant sources do not contain a GPA, so the backend refuses to invent one. |
| 2:30–3:15 | Submit whitespace, then ask for the staff memo | Show validation and the neutral denied response. |
| 3:15–4:00 | Explain browser -> Next proxy -> FastAPI -> checked evidence/output | Citation IDs and quotes are checked; semantic completeness remains a limitation. |
| 4:00–5:00 | Stop the mock backend, submit again, and show recorded test results | Demonstrate a network failure without a fabricated answer. Distinguish local checks from hosted CI and live AI. |

## Real adapter mode (separate approval for paid requests)

Use the existing isolated app, not the shared production main.py:

```powershell
Set-Location 'C:\CampusPilot\Campus-Pilot'
.\.venv\Scripts\python.exe -B -m uvicorn ai.demo_api:app --host 127.0.0.1 --port 8002
```

It uses the previously seeded ignored database. Set Terminal B's AI_API_BASE_URL
to `http://127.0.0.1:8002` and restart Next.js. Without AI_API_KEY and a compatible
AI_MODEL in the Python process, supported questions return unavailable; no model
success is claimed. If credentials are present, asking supported questions can
incur a paid request. Obtain explicit approval first and never paste keys into
chat or client code. Existing .env files are not automatically loaded by this app.

To guarantee no provider access while inspecting real-adapter failure behavior,
use the following instead in Terminal A. Only the child process loses its keys:

```powershell
@'
import os
os.environ.pop('AI_API_KEY', None)
os.environ.pop('AI_MODEL', None)
import uvicorn
uvicorn.run('ai.demo_api:app', host='127.0.0.1', port=8002)
'@ | .\.venv\Scripts\python.exe -B -
```

## Checks and results

Repository root:

```powershell
.\.venv\Scripts\python.exe -B -m unittest discover -s tests -v
git diff --check
git status --short --untracked-files=all
```

Frontend directory:

```powershell
node --test tests/ai-proxy.test.mjs
node node_modules/eslint/bin/eslint.js app/ai app/api/ai lib/ai-contract.ts tests/ai-proxy.test.mjs
node node_modules/typescript/bin/tsc --noEmit --incremental false
npm run lint
npm run build
```

Verified during implementation on 2026-10-26:

- Python: 71 tests passed, no failures/errors.
- Node contract/proxy tests: 7 passed, no skips/failures; all upstream calls mocked.
- Focused lint on new frontend files: passed.
- TypeScript: passed; production build: passed with installed Next.js 16.4.3.
- Full frontend lint: FAILED on the existing homepage's `any[]` type. That page
  was intentionally not modified by this integration.
- Browser: mock answer with citation, missing-GPA fallback, empty-input validation,
  and stopped-backend error verified. Mobile viewport 390px had no horizontal overflow.
- Origin normalization regression: the proxy compares browser Origin to the actual
  Host because Next can normalize request.url to localhost for a 127.0.0.1 request.

The manifest/lockfile still specify Next 16.4.0 while installed Next is 16.4.3;
dependencies were not changed. Build validation therefore covers the installed
version only. Existing multiple-lockfile root warnings remain. No CI change was
made for S3-03, and the new Node tests are not yet wired into GitHub Actions.

### Resumed verification on 2026-10-26

The existing implementation was preserved. Fresh checks again passed: Python 71
tests, Node 7 tests (zero failures/skips), focused frontend lint, TypeScript, and
the production build. Full lint again reported only the pre-existing homepage
`any[]` error. No dependency or CI changes were made to resolve unrelated warnings.

Fresh browser checks used a temporary mocked backend on 8013 and the built frontend
on 3004. Enrollment/citation, GPA fallback, empty validation, mocked 503 status,
and stopped-backend 502/network error were observed. At 390px viewport width,
document width was also 390px. A delayed browser interception probe timed out in
the test harness after showing the loading message and disabled input/button;
a separate immediate mocked 503 check passed. This is not evidence of a real
provider timeout test in the browser; provider failures are covered by mocked
Python tests. Test-only server processes were stopped after verification.

Recovery found an additional, unrelated root package-lock.json edit adding only
the root package name `Campus-Pilot`. No version changes were in that diff. It was
left untouched and should be reviewed separately before staging S3-03. Nothing
was staged, committed, pushed, or merged during recovery.

| Adviser requirement | Current evidence | Readiness |
| --- | --- | --- |
| End-to-end AI feature through backend | Browser -> proxy -> SQLite/retrieval -> mock -> checked response verified | Partially complete: genuine model success still requires approval and verification |
| Backend processing of AI output | Structure, excerpt/citation checks and API tests pass | Locally complete for the documented extractive scope; not semantic proof |
| Small evaluation dataset | 14 fictional scenarios exercised in the passing Python suite | Locally complete; not a live-model quality evaluation |
| Mocked LLM tests in CI | Python CI step exists from S3-02; local tests pass | Partially complete: no hosted run verified; new frontend tests are not in CI |
| Safe failures | Provider/malformed-output mocks and browser fallback/network checks | Locally complete for tested cases; not production reliability certification |

## Remaining consultation work

The frontend -> Next proxy -> FastAPI -> mock generator -> validated response
path is demonstrated. A genuine live LLM answer is NOT verified. Hosted CI and
deployment are NOT verified. The separate static prototype and remote departments
page remain unchanged, including the existing remote-fetch issue.

Coordinate dependency alignment and the existing lint issue with Josiah/Cassie.
Review and approve S3-03 before committing/pushing. S3-03 starts from local S3-02
checkpoint 1d60484 and depends on that backend work. No merge or PR was performed.

Beginner explanation: Next.js safely relays a question to FastAPI, checks the
reply's shape, and displays the backend's answer and source labels.
ELI5: the website is a question window; a messenger takes the question to the
librarian and brings back either labeled reading cards or an honest limitation.
