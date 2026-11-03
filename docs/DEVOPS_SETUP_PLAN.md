# CampusPilot CI/CD setup plan

Prepared November 4, 2026 (Asia/Manila). This is a proposal, not a deployed setup.
Reference: the supplied For DevOps.pdf, Module 03. Its sample workflow and fictional
metrics are examples, not CampusPilot results.

## Current evidence

- `.github/workflows/ci.yml` runs on pushes and pull requests targeting `main`.
  It installs demo Python requirements, runs unittest and pytest, builds the
  frontend with `npm ci`, and runs the frontend proxy tests.
- The pytest step receives OpenAI and Pinecone secrets. Offline checks should
  instead prove they run without provider credentials or paid calls.
- The workflow does not run frontend lint or explicit TypeScript checks, and
  does not declare deployment, migration, smoke-test or security-scan jobs.
- The local `staging` branch exists. Current workflow triggers do not cover it.
- `frontend/package.json` provides a lint script; frontend proxy tests use Node's
  built-in runner. There is no `npm test` script to copy from the PDF example.
- No Render deployment configuration or metrics log was found in this inspection.
  Host integrations may exist outside the repository and remain unverified.
- The user reports rotating the Supabase password, updating Render, and receiving
  a successful local `/departments` response. These are user-reported results.

## Proposed implementation, in order

1. With explicit approval, update the existing CI workflow to cover pull requests
   and pushes to both `staging` and `main`. Use read-only repository permissions,
   bounded job timeouts and cancellation of superseded PR checks. Do not cancel
   an in-progress production deployment.
2. Separate frontend and backend verification jobs so independent checks run in
   parallel. Keep Python and Node versions aligned with the team's supported
   runtimes; review upgrades separately.
3. Run backend tests with fictional fixtures, temporary SQLite and no production
   credentials. Inspect test imports first, select one test runner where it covers
   the complete suite, and retain Alembic configuration tests with their required
   dependencies. Do not run migrations against Supabase from PR checks.
4. Run frontend install, lint, TypeScript, proxy tests and build. Resolve any
   existing lint/build failures with Josiah rather than weakening the checks.
5. Choose dependency and secret scanning tools with Cassie. Add meaningful gates
   after reviewing compatibility, installation needs and existing findings.
6. Configure branch protection in GitHub for `main` and `staging`: reviewed PRs,
   required checks, up-to-date branches, no force pushes and no deletion. Choose
   required check names after the workflow has produced an actual hosted run.
7. Configure staging hosting separately from production. A branch named staging
   alone does not isolate a database, credentials, model budget or deployed app.
   Use fictional seed data for previews and staging.
8. Configure Render/Vercel to deploy the agreed branch only after checks pass.
   First inspect the actual hosting setup to avoid duplicate or premature deploys.
   Select either host-managed deployment or an Actions deployment job with the
   owners. Record deployed commit IDs and a read-only smoke-check result.
9. Review migration ordering, backups and rollback with Brian and Cassie before
   enabling automated migrations. The current provenance revision assumes an
   existing document_chunks table; it is not proof of an empty-database bootstrap.
10. Record real pipeline timings and deployment outcomes. Never copy example
    numbers from the PDF. A scheduled paid model smoke test needs separate approval
    and a budget; mocked model tests stay in ordinary CI.

## Verification before enabling deployment

- Inspect workflow syntax and test collection with installed tools, without
  installing dependencies unless separately approved.
- Run backend offline tests and frontend lint, type check, proxy tests and build
  using the agreed dependency versions. Record failures and unavailable tools.
- Verify a hosted PR run on its actual commit. Local success is not hosted CI.
- Test the staging release with fictional data, then verify the deployed commit
  and database-backed read. A welcome-page response alone is insufficient.
- Check that a failed required check blocks merging and deployment.
- Document how to roll back application code and how to handle schema changes.
- Protect CRUD routes with authentication/authorization before public use;
  database password rotation does not implement API access controls.

## Decisions needed

- Approve the scoped CI changes in steps 1-4, with no deployment or paid calls.
- Confirm whether staging has a separate Render service and database.
- Confirm frontend hosting and the intended staging-to-main promotion process.
- Obtain separate scoped approval for hosted settings, installs, migrations,
  production access, commits, pushes, PR creation and deployment as applicable.

## Approved first-phase changes and verification

The user approved steps 1-3 of the chat proposal: staging/main CI coverage,
frontend lint/type checks, and mocked checks without provider secrets. The
workflow now targets both branches, removes provider secret injection, explicitly
sets in-memory SQLite for both Python test steps, and runs frontend lint, type
checks and proxy tests before building. Existing runtime versions and test runners
are preserved. Permissions, job splitting and other hardening above remain proposals.

`frontend/app/page.tsx` replaces its existing `any[]` state with a Department type
containing numeric id and string name so the new lint gate passes.

Local checks on November 4, 2026:

- `py -B -m unittest discover -s tests`: 106 passed, no skips, using installed
  Python 3.15 and explicit in-memory DATABASE_URL; includes temporary SQLite
  migration checks. Initial sandbox run failed on Windows temporary-directory
  access; the outside-sandbox retry passed. CI Python 3.13 was not tested locally.
- `node --test tests/ai-proxy.test.mjs`: 7 passed with mocked fetch, after retrying
  outside the sandbox because test-worker spawning was blocked.
- `node node_modules/eslint/bin/eslint.js .`: passed after the Department type fix.
- `node node_modules/typescript/bin/tsc --noEmit --incremental false`: passed.
- `npm run build`: passed with installed Next.js 16.4.0 after a network-enabled
  retry for Google Fonts. Existing multiple-lockfile warning remains.
- `git diff --check`: passed.

No local pytest run (pytest unavailable), dependency installs, hosted CI verification,
commits, pushes, deployments, paid model calls or production database operations.
The earlier current-evidence section describes the pre-change workflow.
