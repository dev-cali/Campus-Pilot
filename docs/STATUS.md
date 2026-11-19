# CampusPilot status

## 2026-11-17 — Coverage checkpoint evidence

- Implemented in the local working tree: a single-call internal `parts` contract
  with at most two declared question excerpts, strict fields, sequential indexes,
  exact source quotes, support consistency, and deduplicated trusted citations.
  Declared partial support abstains without citations; malformed output fails
  safely. Empty parts represent whole-question abstention, including overflow.
  Public responses, eligibility and source revalidation remain intact.
- Semantic limits: model-declared parts do not prove that every request was
  included or that quotes answer the question. Explicit omission/relevance tests
  remain. Retrieval is sensitive to wording; live multi-part behavior is unverified.
- Historical offline results from this session, not rerun for this entry:
  adapter 15 passed; full Python suite 123 run, 122 passed, one Alembic-unavailable
  skip. Subsequent test/mock refinements: focused answer-API suite 12 passed,
  including realistic two-part evidence and documented mock-demo compatibility.
  The full suite predates those refinements. Mock success is not live-model quality.
- User-observed live evidence, recorded today: after correcting the backend key,
  one manual frontend submission of "What do fictional learners review for
  enrollment?" returned HTTP 200 and the sample-course-list excerpt, citing
  fictional enrollment document 103, page 1, version v1. Reported configuration:
  backend 127.0.0.1:8002, frontend localhost:3000, model gpt-5-mini, completion
  limit 1000. No request was repeated by the agent. This verifies one reported
  live example, not general completeness, retrieval quality, or production readiness.
- Integration cautions: code defaults to 400 completion tokens; the larger parts
  payload can truncate, and the successful runtime used 1000. The modified proxy
  defaults to port 8001, so the reported setup requires an explicit port-8002
  override. Cached upstream is five commits ahead; no fetch or synchronization
  occurred. The final checkpoint subset has not been independently tested.

Proposed checkpoint: [answer service](../ai/answer_service.py),
[provider adapter](../ai/llm_client.py), [retrieval budgets](../ai/local_retrieval.py),
[demo API readiness](../ai/demo_api.py), [adapter tests](../tests/test_llm_client.py),
[answer API tests](../tests/test_answer_api.py),
[evaluation cases](../tests/fixtures/ai_eval_cases.json),
[mock server](../tests/frontend_demo_server.py), and this status document.
Include existing diagnostics/budget dependencies together; this is a bounded
answer-validation checkpoint, not a coverage-only patch.
Exclude the frontend input/proxy edits and database-configuration test changes
from this checkpoint, preserving them locally for separate review.

Suggested commit message: `feat(ai): validate bounded evidence coverage and preserve demo flow`

Next proposed improvement: an offline paraphrase regression set for retrieval
of both requested fictional facts, measuring omissions before changing ranking.


## 2026-11-17 — Reconciled PR verification

- Recovered the existing coverage branch in a persistent worktree on staging
  `0b2e0be97369b67fceda5bc24b68ae484cb72229`. Upstream readiness checks and retrieval
  budgets were already equivalent and require no new diff. Preserved upstream
  diagnostics, source revalidation, timeouts, zero retries and public responses.
- Fresh offline worktree checks: adapter 15 passed; answer API 12 passed.
  Full discovery: 95 run, 92 passed, two import errors, one Alembic-related skip.
  Both errors are missing `jwt` in the existing environment, affecting upstream
  authentication and backend CRUD test imports. No dependencies were installed;
  the full suite is not verified on this baseline.
- Application imports resolved to this worktree. External connections were
  blocked; no paid requests occurred. Earlier full-suite results apply only to
  the older baseline. Live evidence above remains user-observed, single-question
  evidence; no additional live test was run.
