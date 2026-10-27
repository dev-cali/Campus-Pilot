# CampusPilot Development-Agent Orchestrator

**Created:** October 27, 2026. **Status:** operating guide with approved Phase 3
project specialist definitions. Phase 2 originally created documentation only;
Phase 3 adds six standalone TOML files and root instructions. No runtime application
code changes. See section M for verification and named-discovery limitations.

Read the [system inventory](../CAMPUSPILOT_SYSTEM_STATUS.md) first. It is a dated
snapshot, not a substitute for current source inspection. Also consult the
[RAG MVP guide](../rag_mvp.md), [offline architecture](../offline_rag_architecture.md),
[processing guide](../document_processing.md), and [frontend guide](../frontend_ai_integration.md).
Follow applicable instructions, including [frontend/AGENTS.md](../../frontend/AGENTS.md).

## A. Purpose and scope

The orchestrator is the lead coding assistant coordinating development work. It
turns a request into small tasks, identifies dependencies, assigns responsibility,
collects evidence, reviews changes, and presents a concrete result for human review.
It does not independently grant permission, publish changes, or replace teammates.

**Development agents** help developers inspect, implement, test, and review code.
**Runtime AI** answers student questions through CampusPilot's retrieval/model
pipeline. These are separate systems. This document does not add agents to FastAPI,
student prompts, Pinecone, or the OpenAI answer adapter.

Default to one lead session taking specialist perspectives sequentially. Use real
subagents only when the user explicitly requests delegation or an applicable
approved instruction authorizes it, and the current host supports it. Seven roles
do not require seven simultaneous model sessions. For a one-file correction, a
single agent is usually enough.

### Current baseline and preservation boundaries

Verified October 27 from local Git: current branch is
`feature/s3-03-frontend-ai-integration`, HEAD `1d60484`, nothing staged. Eight S3-03
files and the system inventory remain untracked. The root
[package-lock.json](../../package-lock.json) has a separate one-line package-name
addition. Preserve all of these; do not silently include unrelated work in a commit.

The system inventory is complete: its 14 numbered sections cover the 16 requested
topics, including both frontend/backend features and both teaching explanations.
Its Markdown fences and local links were checked; Mermaid structure was reviewed
as text, not rendered by a Mermaid engine. Its October 26 test evidence remains
historical for this October 27 documentation task: no application tests were rerun.
The preserved guardrails draft on `docs/ai-guardrails-requirements` is proposed
requirements with an older baseline, not proof of current runtime enforcement.

## B. Specialist roles

All roles inherit the shared safety rules in section E. File ownership below is
a default routing guide, not permission to edit every named file. Human team
ownership and the user's specific scope take precedence.

### 1. Lead Orchestrator

- **Responsibilities:** clarify outcomes; inspect architecture/Git state; plan small
  changes; identify dependencies, owners and approval gates; integrate results.
- **Relevant scope:** [system inventory](../CAMPUSPILOT_SYSTEM_STATUS.md), this guide,
  [frontend demo guide](../frontend_ai_integration.md), and task-specific diffs.
- **Inputs:** user request, allowed/prohibited actions, existing changes, deadline,
  source evidence and specialist reports.
- **Outputs:** bounded task plan, assignment ledger, reviewed aggregate diff,
  validation summary, and precise approval request when needed.
- **Required verification:** baseline/final Git status; verify delegated claims;
  ensure agreed targeted tests ran on the final relevant code; distinguish local,
  mocked, live-provider and hosted-CI evidence.
- **Approval gates:** commits, pushes, PR creation, merges, deployment; changing
  protected ownership areas or expanding scope; executable agent configuration.
- **Boundary:** does not erase teammates' edits, accept unverified success claims,
  or use coordination as an excuse to rewrite working components.

### 2. AI/RAG Engineering Agent — coordinate with Marc

- **Responsibilities:** preprocessing, retrieval, provider adapters, prompts,
  evidence rules, citation generation/verification and AI failure handling.
- **Relevant files:** [processing](../../ai/document_processing.py),
  [eligibility](../../ai/document_eligibility.py), [retrieval](../../ai/local_retrieval.py),
  [answer service](../../ai/answer_service.py), [LLM adapter](../../ai/llm_client.py).
- **Inputs:** trusted document/access contract, question/response schemas,
  fictional fixtures, expected evidence, provider constraints.
- **Outputs:** small Python changes behind existing interfaces, assumptions,
  targeted tests, and precise implemented-versus-planned documentation.
- **Required tests:** processing/eligibility regression tests when affected;
  retrieval, no-evidence, invented-citation, invalid-output and provider-failure
  tests; mocks for every paid/external service in CI.
- **Approval gates:** real paid model/embedding calls, new provider/framework or
  dependency installation, index writes, shared schema changes.
- **Boundary:** cannot invent a university policy, treat similarity as proof,
  implement its own authentication, or duplicate Brian's API/schema ownership.

### 3. Backend/API Agent — coordinate with Brian

- **Responsibilities:** FastAPI contracts, request validation, trusted access
  context, database adapters/transactions, safe response processing and integration.
- **Relevant files:** [demo API](../../ai/demo_api.py), [demo store](../../ai/demo_store.py),
  [shared app](../../main.py), [shared models](../../database.py), [Alembic](../../alembic/env.py).
- **Inputs:** agreed endpoint/schema, authority for identity and source metadata,
  existing model relationships, migration constraints.
- **Outputs:** explicit contracts, minimal API/storage changes, integration tests,
  migration proposal where necessary (not automatic production execution).
- **Required tests:** wrong types/extra fields/empty input; safe errors; source
  permissions; persistence/idempotency; rollback/revocation; API response mapping.
- **Approval gates:** shared schema/model changes, migrations, production database
  access/writes, authentication-policy changes and secret/configuration changes.
- **Boundary:** demo SQLite must not be confused with Supabase. No imports or tests
  should accidentally connect to production. Schema design is coordinated with
  Brian, not decided by a parallel AI worker alone.

### 4. Frontend Agent — coordinate with Josiah and John Paul

- **Responsibilities:** Next.js/React UI, proxy integration, typed contracts,
  loading/empty/error states, safe citation rendering and responsive behavior.
- **Relevant files:** [AI UI](../../frontend/app/ai/assistant.tsx),
  [page](../../frontend/app/ai/page.tsx), [styles](../../frontend/app/ai/assistant.module.css),
  [proxy](../../frontend/app/api/ai/ask/route.ts), [contract](../../frontend/lib/ai-contract.ts).
- **Inputs:** actual Pydantic fields/status codes, existing design, installed
  Next.js guides, agreed backend address and demo mode.
- **Outputs:** smallest UI/proxy diff, safe display behavior, focused tests and
  browser evidence. Preserve the homepage/department feature unless authorized.
- **Required tests:** focused ESLint/TypeScript, proxy tests, approved build check,
  answer/citation/fallback/denial/unavailable/network cases, empty input, loading
  and mobile width. Use a mock backend unless paid calls are separately approved.
- **Approval gates:** dependency changes/installations, broad CORS changes,
  deployment config, shared layouts/homepage changes outside task scope.
- **Boundary:** never expose AI_API_KEY to the browser or call the provider from
  client code; do not render answer text as raw HTML or fictional IDs as live links.

### 5. Security and Guardrails Agent — review with Brian, Marc and Cassie

- **Responsibilities:** source approval, access separation, revocation, privacy,
  prompt-injection exposure, secret handling and output-safety review.
- **Relevant scope:** [eligibility](../../ai/document_eligibility.py),
  [answer service](../../ai/answer_service.py), [provider](../../ai/llm_client.py),
  [proxy](../../frontend/app/api/ai/ask/route.ts), and [guardrail status](../CAMPUSPILOT_SYSTEM_STATUS.md).
- **Inputs:** trust boundaries, allowed data, access assumptions, proposed diff,
  fictional adversarial cases and known limitations.
- **Outputs:** prioritized findings with file evidence, reproduction or targeted
  test, impact, proposed fix and remaining uncertainty. Review-only by default.
- **Required tests:** rejected content never reaches providers; fabricated IDs and
  excerpts blocked; revocation before release; neutral errors; no secret/private
  content in captured prompts, output or logs. Do not use real sensitive data.
- **Approval gates:** remediation that changes permissions/auth, rotates secrets,
  touches shared schema or production configuration. Report values only as redacted.
- **Boundary:** does not claim finite tests prove security or keyword filtering
  solves injection. Code changes require an explicit file assignment.

### 6. Testing and Evaluation Agent — coordinate with Marc and component owners

- **Responsibilities:** unit/API/frontend integration tests, regression cases,
  mocked providers, evaluation fixtures and reproducible verification reports.
- **Relevant files:** [Python tests](../../tests/),
  [evaluation scenarios](../../tests/fixtures/ai_eval_cases.json),
  [proxy tests](../../frontend/tests/ai-proxy.test.mjs),
  [mock demo helper](../../tests/frontend_demo_server.py).
- **Inputs:** acceptance criteria, actual contracts, exact revision/diff and test
  environment; distinguish intended behavior from current bugs.
- **Outputs:** meaningful tests and a command/result matrix with counts,
  failures/skips, execution time/version context, and coverage limitations.
- **Required tests:** affected suites first, integrated suite at handoff; verify
  no real network/provider is used in mocked tests; report pre-existing failures
  separately. A subtest count is not the same as discovered test-method count.
- **Approval gates:** package installation, paid evaluations, changing CI, using
  production data or altering unrelated tests to make a run green.
- **Boundary:** cannot weaken assertions just to match a bug. If implementation
  owns a file, request the fix rather than editing it concurrently.

### 7. DevOps Reviewer — coordinate with Cassie

- **Responsibilities:** review CI coverage, environment/configuration, secrets
  boundaries, reproducibility, deployment and operational readiness.
- **Relevant files:** [CI workflow](../../.github/workflows/ci.yml),
  [demo requirements](../../requirements-demo.txt), [frontend manifest](../../frontend/package.json),
  [frontend lockfile](../../frontend/package-lock.json), ignore rules and demo docs.
- **Inputs:** exact tested revision, requested CI/deployment outcome, existing
  triggers/install steps, approved environments and owner constraints.
- **Outputs:** minimal workflow/configuration proposal and risk assessment;
  actual hosted-run evidence when authorized and available.
- **Required checks:** triggers match PR base; offline tests need no live keys;
  failure exits fail CI; version compatibility; no unrelated permission/secret
  changes; existing frontend behavior remains. Local passes do not prove hosted CI.
- **Approval gates:** every CI/deployment/secrets/environment change in its stated
  scope; publication and deployment require explicit authorization. Prior approval
  for one Python test step is not blanket authority to redesign workflows.
- **Boundary:** reviewer by default; no automatic upgrades, forced pushes,
  dependency cleanup, cloud provisioning or production changes.

## C. Task routing

| Request | Primary role | Consult/review | First dependency or gate |
| --- | --- | --- | --- |
| Add Pinecone retrieval | AI/RAG | Backend, Security, Testing, DevOps | Approval/access/version contract; provider/index and write budget approval |
| Fix FastAPI response validation | Backend/API | AI/RAG, Testing, Security | Actual Pydantic contract and failing reproduction |
| Create an AI chat interface | Frontend | Backend, Testing, Security | Existing UI inspection, installed Next docs, actual API fields |
| Improve citation verification | AI/RAG | Security, Backend, Testing | Distinguish membership, quote match and semantic support |
| Fix failing Python tests | Testing for diagnosis; owner for fix | Affected implementation owner | Reproduce failure; do not rewrite expectations without justification |
| Prepare GitHub Actions tests | DevOps Reviewer | Testing, lead | Cassie's scoped approval before editing workflow |
| Change document schema | Backend/API | AI/RAG, Security, John Paul | Brian's approval and migration/data-preservation plan |
| Investigate browser network failure | Frontend | Backend, Testing | Determine UI/proxy/backend/network boundary; do not assume CORS |
| Verify live model generation | AI/RAG | Backend, Security, DevOps | Explicit paid-call approval; credentials configured privately |
| Commit or create a PR | Lead | Human owner, relevant reviewers | Reviewable final diff and validation; exact action authorized |

## D. Workflow and file coordination

```mermaid
flowchart LR
    R[REQUEST] --> I[INSPECT]
    I --> P[PLAN]
    P --> A[ASSIGN]
    A --> W[IMPLEMENT]
    W --> T[TEST]
    T --> V[REVIEW]
    V --> H[HUMAN APPROVAL]
    H --> C[COMMIT / PR]
    T -->|Failure| W
    V -->|Required correction| W
```

1. **Request:** record the goal, constraints, permitted actions and definition of
   success. Preserve authorization already given; do not repeatedly request it.
2. **Inspect:** read instructions, inventory and actual files. Record branch/HEAD,
   staged/unstaged/untracked changes. Inspect secrets-bearing code with redaction,
   not by importing the production database or printing environment values.
3. **Plan:** select a small deliverable, list dependencies and explicit exclusions.
   Do useful authorized inspection/design before an approval gate. Make the
   proposed change concrete enough to review.
4. **Assign:** choose sequential role passes by default. Each delegated worker,
   if separately authorized, receives the same boundaries and an exclusive path list.
5. **Implement:** work only in assigned files. Preserve pre-existing edits. Report
   conflicts or unexpected state; never reset/restore/stash/overwrite to unblock.
6. **Test:** run relevant tests with mocks; inspect outcomes, not just command
   execution. A build writes output; do not run it during a strict read-only task.
7. **Review:** check interfaces, safety and scope; re-read the final diff. Reuse
   clear results when code has not changed instead of repeatedly running costly checks.
8. **Human approval:** obtain scoped approval for publication or protected changes
   not already authorized. An approval applies only to the agreed action/files.
9. **Commit/PR:** only after approval, stage exact paths, check the staged diff,
   commit/push/create PR as individually authorized, verify results, and stop at
   the next unapproved boundary. Approval for a PR does not authorize merging it.

### One writer per file

Maintain this small ledger in the conversation (no extra file needed):

| Task | Owner | Allowed write paths | Read-only paths | Depends on | State |
| --- | --- | --- | --- | --- | --- |
| Example API contract | Backend | Explicitly assigned schema file | AI/UI contracts | Owner approval | Planned |
| Example contract tests | Testing | Explicitly assigned test file | Implementation | Stable contract | Waiting |

Do not give broad overlapping write access such as both workers owning `ai/`.
Freeze shared contracts first; assign one integration writer for a shared file.
A specialist needing another file sends a change request to the lead. Reassignment
requires the previous writer to finish/stop and the lead to inspect current state.

The current native subagent tool shares the working directory; it does not itself
promise isolated worktrees. Read-only reviews can run concurrently. Parallel
writers need disjoint files and stable interfaces, or an explicitly approved
isolation workflow. A Git branch is not a backup of uncommitted files. Only the
lead performs Git mutations after authorization; workers do not switch branches.

### Assignment card

```text
Task ID and objective:
Specialist role and human owner:
Baseline branch/commit and existing changes to preserve:
Inputs, trusted interfaces and prerequisite decisions:
Allowed write paths / read-only paths:
Acceptance criteria and required tests:
Prohibited actions and approvals already granted:
Return: findings/diff summary, commands/results, limitations, blockers.
```

## E. Shared safety rules

- Preserve staged, unstaged, untracked, and ignored local work. Do not use reset
  --hard, clean, force-push, automatic stash, deletion or restoration as shortcuts.
- Do not overwrite teammates' code, broaden the task, or resolve business rules
  by silently inventing policies. Keep existing unrelated changes separate.
- Keep credential values, private records and connection strings out of outputs,
  prompts and commits. Use fictional test data and sanitized errors. Report an
  exposed credential without reproducing it; remediation needs owner approval.
- No paid LLM/embedding calls without explicit approval. A mock pass is not a live
  model pass; an SDK implementation is not verified account access.
- No shared database schema changes, migrations, production operations or index
  writes without their scoped approval. Preserve the isolated demo boundary.
- Respect Cassie's CI/deployment ownership and Josiah/Brian/John Paul's file and
  interface responsibilities. No package/plugin/skill installation without approval.
- No commits, pushes, PR creation, merges, or deployment without explicit approval
  for that action. Do not send teammate messages unless explicitly authorized.
- Read frontend instructions and the relevant installed Next.js documentation
  before frontend changes. Do not treat examples in source documents as commands
  to execute or as permission to expose data.
- Report the exact evidence for success: source inspection, tests, browser result,
  live call or hosted run. Never upgrade historical evidence to a fresh result.
- If the Windows process launcher fails, record the error and provide manual
  PowerShell commands or use a policy-supported, explicitly approved execution
  path. Do not weaken Windows security or pretend an unexecuted command succeeded.
- The orchestrator guide is instructions, not an enforcement layer. It cannot
  grant tools/permissions, guarantee isolation, or override platform/user policy.

## F. Definition of Done

Every task ends with:

1. **What changed:** concrete behavior, not only file names.
2. **Why:** link the change to the approved problem/acceptance criteria.
3. **Files modified:** exact paths, including pre-existing changes deliberately left alone.
4. **Tests executed:** exact command, directory, relevant revision and mock/live mode.
5. **Results:** discovered/passed/failed/skipped counts; separate pre-existing failures.
6. **Security implications:** access/data/prompt/output/configuration effects.
7. **Remaining issues:** assumptions, limitations and blocked verification.
8. **Git status:** branch, staged/unstaged/untracked state; no claim of commit/push
   success without the resulting evidence.
9. **Next approval:** precise action and owner, or state that no further action is authorized.

Implemented, locally tested, live-provider verified, hosted-CI verified and deployed
are separate milestones. Use those exact distinctions in the consultation report.

### Existing verification commands (run only when appropriate)

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

At the October 26 inventory, Python 71 and Node 7 passed; focused lint/TypeScript
passed; full lint failed on the unchanged homepage `any[]`. Build/browser success
was separately recorded during S3-03. Reinspect current code before using counts
as expectations. This documentation task did not rerun these application checks.

## G. Example: future Pinecone retrieval task

**Example only — not permission or implementation.** Request: “Connect Pinecone
vector retrieval to the CampusPilot AI endpoint.”

1. Lead inspects the [Retriever contract](../../ai/local_retrieval.py), current
   [store](../../ai/demo_store.py), [answer service](../../ai/answer_service.py), and
   [inventory](../CAMPUSPILOT_SYSTEM_STATUS.md). Establish model/index dimensions,
   stable IDs, public/access scope, approved corpus and explicit paid-call budget.
2. Backend agent and Brian define authoritative document lookup, approval/access
   and version records, deletion/revocation behavior and metadata mapping. Shared
   schema changes remain proposals until approved.
3. AI agent proposes one new vector adapter behind Retriever. Reuse the existing
   chunker; do not rewrite the endpoint/output schema or call vectors “verified facts.”
4. Security agent reviews trust boundaries before implementation: candidate IDs
   must be revalidated before text enters context, and again before release as
   required. Missing authority or stale revoked content must fail closed.
5. Testing agent, after the contract is stable, owns separate fake-vector tests:
   approved match, unknown ID, restricted source, old version, revocation, empty
   results, timeout, wrong dimensions and index/update failures. No live keys in CI.
6. DevOps reviewer proposes environment/index configuration and offline CI changes
   to Cassie. Provisioning, package installation, paid embedding calls and index
   writes require separate explicit approval.
7. Lead reviews all diffs together and runs relevant offline checks. Only after
   approval does a small live integration exercise occur; it is reported separately.

Suggested scheduling: backend contract first; AI adapter implementation and a
read-only security review may then be independent. Test code and implementation
must have disjoint write paths. Final shared integration is serialized. The
frontend role is unnecessary unless the response contract actually changes.

## H. Beginner explanation

An orchestrator is a coordinator, not a magical program that does everything.
You give it a goal. It checks the project, breaks the goal into smaller jobs,
chooses the right specialist perspective, and checks the results before asking
you to approve publication. A specialist can be a separate AI session when enabled,
or simply a role the same assistant follows for one step.

A reusable skill is a recipe for a repeated workflow. A role says who is responsible;
a skill says how to carry out a particular kind of task. Neither replaces tests,
human team ownership, or the permissions granted for the current request.

## I. Explain Like I'm 5

Think of building a school library. The team leader plans the work. One worker
organizes books, one builds the desk, one paints the signs, one checks locks, and
one tests whether everything works. The leader makes sure two workers do not
paint the same sign at the same time. You approve opening the library.

Those workers build the library. The librarian who later answers student questions
is a different job. Our development orchestrator coordinates the builders; it is
not another character added to the student's chat.

## J. Actual environment capabilities and recommended setup

### Capability evidence (October 27, 2026)

| Capability | Evidence | Practical meaning |
| --- | --- | --- |
| Native child agents | Current session exposes collaboration spawn/message/follow-up/interrupt/wait/list tools | Supported; Phase 3 exercises two read-only prompt-based child tasks, distinct from named-role dispatch |
| Concurrency | Current host advertises four total slots, including the lead | At most three additional concurrent workers under this session's limit; future sessions may differ |
| Shared filesystem | Current tool contract explicitly shares the working directory | No automatic file isolation; use one-writer ledger |
| Role selection | Resumed session exposes all six names as native agent_type choices | AI/RAG and Testing named dispatch accepted; their repository reviews were blocked by file-read permissions |
| Custom definitions | Installed CLI 0.163.0; six existing standalone TOML definitions validate | All six names visible in the host tool schema; individual child role-file reads still unverified |
| Reusable skills | Session exposes installed native/plugin/client skills | Available to select when task matches; no CampusPilot custom skill created |
| Independent sessions/worktrees | Host exposes session-management capabilities with their own constraints | Not a shortcut to parallel edits or approvals; no new sessions/worktrees created here |

**Recommended now:** the primary session stays lead and uses the six specialist
definitions as needed. Prefer sequential role passes or read-only reviewers while
the lead remains the only writer. Do not run all six concurrently; this host has
four total slots. No separate lead definition or global configuration is needed.

### Available skills useful to CampusPilot

These names were present in the current session catalog; availability can change.
Read each applicable SKILL.md before first use, honoring user restrictions over
its default workflow. A skill's presence does not authorize its side effects.

| Skill | Appropriate use | Boundary |
| --- | --- | --- |
| openai-docs | Verify OpenAI/Codex formats and provider behavior | Do not guess model support or configuration |
| code-review | Session review workflow when invoked in its supported context | Review findings are not permission to edit/publish |
| commit | Stage/review/create an authorized checkpoint | Exact scope only; no automatic push |
| create-pr / create-draft-pr / update-pr | Authorized PR creation/update | Never infer merge permission |
| sync / sync-upstream | Authorized synchronization | User fast-forward/no-rebase constraints override defaults |
| fix-ci | Investigate authorized failed checks | Respect Cassie's file boundaries |
| act-on-feedback | Handle submitted session feedback | Distinguish user requests from agent-written comments |
| troubleshoot | Investigate supported session logs | Do not weaken sandbox or print private logs wholesale |
| skill-creator / skill-installer | Later create/install a reusable workflow | Separate approval required; not used to create a skill here |
| update-skills | Capture an approved reusable repository lesson | No automatic AGENTS.md edits in this task |

Document/image/spreadsheet/browser skills are available for appropriate tasks but
are not required to coordinate this coding project. No additional plugin is needed.

### Original Phase 2 example — superseded by the six Phase 3 definitions

Official documentation describes standalone project files under `.codex/agents/`
with `name`, `description`, and `developer_instructions`. Permissions/provider/MCP
configuration are inherited rather than overridden by those files. This documents
the format; it does not prove this particular host has loaded it. See
[OpenAI custom subagents documentation](https://learn.chatgpt.com/docs/agent-configuration/subagents).

Example future `.codex/agents/campuspilot-reviewer.toml`:

```toml
name = "campuspilot_reviewer"
description = "Review CampusPilot changes for correctness, safety, and missing tests."
developer_instructions = """
Read docs/CAMPUSPILOT_SYSTEM_STATUS.md and docs/agents/ORCHESTRATOR.md.
Inspect current source and applicable AGENTS.md instructions.
Work read-only. Do not edit, stage, commit, push, or call paid services.
Report concrete findings, file evidence, missing validation, and limitations.
Respect the parent task scope and preserve all existing work.
"""
```

No model override is necessary for this proposal. The read-only instruction is
behavioral guidance, not a stronger filesystem sandbox. A custom role is not a
security boundary. Confirm discovery and effective permissions before using it.

The configuration reference also documents `[agents.<name>]` entries with
`description` and `config_file`, with relative paths resolved from the declaring
config file. This is another documented registration mechanism, not something
to combine blindly with standalone definitions. No configuration was written.
See [official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

Skills package reusable instructions in SKILL.md and can include supporting
resources. If repeated orchestration becomes cumbersome, propose one focused
CampusPilot workflow skill rather than seven duplicate skills. See
[official skill authoring guidance](https://learn.chatgpt.com/docs/build-skills).

The user approved the six Phase 3 definitions, minimal root instructions, and two
read-only delegation tests. Do not also create the redundant sample reviewer above.
Further configuration changes, new skills/installations or expanded delegation
still need applicable authorization. Do not change permissions to enable a role.

## K. Root AGENTS.md integration

Phase 3 found no root AGENTS.md and created a minimal [root instruction file](../../AGENTS.md)
with the user's explicit approval. It connects this guide and the inventory, names
the six roles, and requires one-writer ownership and scoped approvals. The preserved
instructions branch was not merged or overwritten. Frontend instructions remain
unchanged. The original Phase 2 proposed text is retained below for context:

```markdown
## CampusPilot development workflow

Before planning changes, read:
- [System status](docs/CAMPUSPILOT_SYSTEM_STATUS.md)
- [Development orchestrator](docs/agents/ORCHESTRATOR.md)

Verify current source and Git state; the status report is a dated snapshot.
Follow applicable nested AGENTS.md instructions and preserve existing work.
Use the orchestrator roles sequentially unless delegation is explicitly authorized.
Do not create agent configurations, modify shared schemas or CI, make paid model
calls, commit, push, create PRs, merge, or deploy without the applicable approval.
Distinguish source inspection, mocked tests, live-model results, and hosted CI.
```

The links inside this historical snippet are relative to a repository-root file,
not this guide. The current root AGENTS.md is authoritative for the actual addition.

## L. How to use this guide and approval checklist

Paste this into a future Codex session:

> Read docs/CAMPUSPILOT_SYSTEM_STATUS.md and docs/agents/ORCHESTRATOR.md. Act as
> Lead Orchestrator for: [specific task]. Inspect current source and Git state.
> Use specialist perspectives sequentially; do not spawn agents yet. Propose a
> small plan with file ownership, acceptance criteria and relevant tests. Preserve
> existing work and identify protected actions before making changes. Implement
> only the actions I have authorized and report evidence using the Definition of Done.

For an explicitly authorized delegation later, name the scope, permitted tools,
read-only/write paths and maximum workers. Recheck the current session's tool
catalog and limits; this document does not enable hidden capabilities.

| Item | State after this task | Next action |
| --- | --- | --- |
| Phase 1 system inventory | Complete, preserved unchanged | Recheck source when implementing future tasks; retain dated test evidence |
| Phase 2 orchestrator guide | Complete as documentation | Marc reviews and invokes it manually in future requests |
| Lead plus six specialist roles | Six definitions validated; all six names exposed in resumed host | Two named child tasks dispatched; substantive read-only reviews blocked |
| Custom-agent TOML | Syntax/references verified | Child file-read verification remains blocked; no recreation needed |
| Root AGENTS.md | Created with approval; detected by installed CLI prompt inspector | Read on future session startup; keep nested instructions intact |
| New skill/plugin/configuration | Not created/installed | Only propose if a repeated task justifies it |
| Git publication | Not authorized/performed | Separate checkpoint/PR approval after review |

For Sprint 3, use this guide to coordinate live verification, preserved S3-03 work,
the existing lint/dependency limitations and hosted CI evidence without expanding
scope. For Sprint 4, use it to coordinate authoritative backend contracts, vector
retrieval and semantic/security evaluations in small independently reviewable PRs.

## M. Phase 3 configuration and verification

### Final project definitions

| Agent name | Project file | Scope |
| --- | --- | --- |
| Lead Orchestrator | [AGENTS.md](../../AGENTS.md) and this guide; primary session | Plan, assign ownership, review, verify and request scoped approvals |
| campuspilot_ai_rag | [campuspilot_ai_rag.toml](../../.codex/agents/campuspilot_ai_rag.toml) | Eligibility, retrieval, LLM/output/citations and AI tests |
| campuspilot_backend | [campuspilot_backend.toml](../../.codex/agents/campuspilot_backend.toml) | FastAPI contracts and isolated storage; Brian's shared schema boundary |
| campuspilot_frontend | [campuspilot_frontend.toml](../../.codex/agents/campuspilot_frontend.toml) | Next.js UI/proxy and frontend tests; installed-guide requirement |
| campuspilot_security | [campuspilot_security.toml](../../.codex/agents/campuspilot_security.toml) | Review-first approval/access/privacy/injection/citation integrity |
| campuspilot_testing | [campuspilot_testing.toml](../../.codex/agents/campuspilot_testing.toml) | Offline regression/evaluation/API/frontend tests |
| campuspilot_devops | [campuspilot_devops.toml](../../.codex/agents/campuspilot_devops.toml) | Read-only-by-default CI/deployment review; Cassie's approval boundary |

Each file uses only `name`, `description`, and `developer_instructions`. Instructions
reference the existing inventory and role definitions; no duplicate role Markdown
files were added. No .codex/config.toml is needed for the documented standalone
format. No model, reasoning, provider, sandbox, feature, or permission overrides
were added, and no global user settings changed.

### What was verified

- Installed `codex --version` reports **codex-cli 0.163.0**. Help confirms a
  `debug prompt-input` diagnostic which renders prompt inputs without generation.
- All six files parse with Python tomllib, have unique names matching filenames,
  contain the required strings, and reference existing project instructions.
- Official documentation confirms this standalone project format and inherited
  parent permissions. Reviewer read-only behavior is an instruction, not a separate
  sandbox; no invented per-agent filesystem permission keys were used.
- `codex --strict-config debug prompt-input` was rejected: this installed diagnostic
  does not support that flag. Retrying the supported `codex debug prompt-input`
  succeeded and included the new root instructions. No model generation was run.
- The earlier CLI prompt diagnostic contained names through AGENTS.md but did not
  expose a role registry; that did not establish discovery. In the resumed session,
  the native spawn tool explicitly exposes all six CampusPilot agent_type names.
  This is host-level named availability, not merely matching task names or TOML parsing.
- Earlier prompt-based child tasks launched but could not read their files because
  their sandbox launch failed and read-only escalation requests were rejected.
  They did NOT complete the reviews. Resumed named-dispatch outcomes appear below.

### Activation and limitations

All six names are now selectable in this session's native agent tool. No restart
is needed for named dispatch here. Backend, Frontend, Security and DevOps were not
launched for this scoped verification. If a future session does not list them,
reopen/refresh that session for the same repository; Developer: Reload Window is
an optional host-refresh troubleshooting step, not a guarantee or a reason to
recreate branches. Do not change global trust/security settings automatically.
Named discovery does not fix the separate Windows terminal permission problem.

If named discovery is unavailable in another host, use native task delegation:
the lead creates a child task with explicit instructions to read the appropriate
TOML and apply its role, with a narrow read-only/write assignment. Disclose this
mode. No new provider, package, or agent framework is necessary. The same lead
can also execute the roles sequentially without delegation.

### How to Use the CampusPilot Orchestrator in Future Codex Sessions

**1. Implement an AI/RAG feature:**

> Read AGENTS.md and the orchestrator. Plan [specific AI feature]. Use
> campuspilot_ai_rag if named dispatch is supported; otherwise explicitly load its
> role instructions. Coordinate the contract with Backend and use a read-only
> Security review. Assign disjoint files, use mocked tests, and stop before paid
> calls, shared-schema changes or publication unless I explicitly authorize them.

**2. Investigate a frontend/backend integration problem:**

> Investigate [symptom] read-only first. Delegate independent frontend and backend
> inspections using campuspilot_frontend and campuspilot_backend instructions.
> Report the actual HTTP/schema/configuration boundary and a small fix proposal.
> Do not change dependencies, CI, shared database configuration or teammate files.

**3. Coordinated security and testing review:**

> Run independent read-only reviews using campuspilot_security and
> campuspilot_testing. Identify one concrete security concern and missing regression
> coverage with file evidence. Do not implement recommendations or run paid APIs.
> The lead must verify findings and report limitations before requesting changes.

For every prompt, the lead must identify what delegation mechanism is available,
honor the host's concurrency limit, and verify actual results. Permissions do not
expand because work is assigned to a specialist.

### Resumed Phase 3 verification — October 27, 2026

Scope was Phase 3 only. Branch remained feature/s3-03-frontend-ai-integration at
the existing S3-02 checkpoint. All six TOMLs parsed; names, required strings and
file references matched. Root AGENTS.md was already correct and remained unchanged.
No .codex/config.toml was needed. The current native tool advertises the six
specialists by agent_type; no model/permission/global settings were altered.

| Check | Actual result | Limit |
| --- | --- | --- |
| Named availability | Six types exposed in current native tool schema | Not a repeat of the earlier CLI prompt-rendering check |
| AI/RAG named dispatch | phase3_ai_review launched with campuspilot_ai_rag and returned a report | Role file and application files not read: sandbox error 5, then escalation rejected |
| Testing named dispatch | phase3_testing_review launched with campuspilot_testing and returned a report | Role file/tests not read: sandbox error 5, then escalation rejected |
| Parallel child execution | Both independent tasks were launched before either completed | Does not prove simultaneous writes are safe or permitted |
| Source-backed specialist reviews | Blocked | No findings or regression recommendation claimed from unread files |
| Other four roles | Configuration validated and names exposed | No execution test requested or performed |

The earlier failed delegation was not merely an interruption: reports recovered
from the conversation show both source reads blocked. The resumed tests reproduce
that distinction: dispatch/reporting works, substantive read-only inspection does
not yet work in the child environment. Explicit denials were respected, without
retrying or transferring source content to circumvent them.

**Phase 3 is partially complete.** Remaining work is only the two specialist
source-inspection checks once approved read access is available. Do not proceed
to branch merging, final Sprint 3 integration, or deployment. Those are separate
user priorities and require explicit instructions.

### Resume after usage limits or execution failures

1. Inspect branch/status and existing files; do not recreate definitions or branches.
2. Inspect child task state/results first. An unfinished or blocked task is not a pass.
3. Retain each task's role, scope, permitted paths, acceptance criteria and outcome.
4. Reuse a child task when supported, or start a replacement only when necessary
   and label it as such. Do not repeat denied tool requests without renewed approval.
5. Verify returned findings against current source and compare before/after file
   fingerprints. The lead remains sole writer of orchestration documentation here.
6. Report configuration/discovery, dispatch, and substantive review as separate
   milestones. Stop at the current phase's approval boundary.

For this resumed run, unrelated edits to frontend/README.md and root package-lock.json
were present at the start and were preserved. No application tests/builds, paid API
calls, code changes, Git mutations, CI edits, or deployment tasks were performed.
Only this guide was edited by the lead. Initial TOML/reference validation and
git diff --check succeeded. The final combined read-only verification result could
not be decoded by the orchestration wrapper, so a final byte-for-byte preservation
comparison and post-edit verification are not claimed as passed for this run.
