# CampusPilot delivery pipeline

Last reviewed: November 4, 2026 (Asia/Manila).

This guide explains the current checks and release process. Workflow details were
verified from the local source. Account settings and deployment results below were
reported by the project owner or shown in their screenshots; they were not audited
through hosting APIs. Remote branches were not refreshed for this documentation task.

## Delivery flow

1. Develop on a feature branch and open a pull request to `staging`.
2. Wait for the `build-and-test` check to pass. Review the changed files.
3. Merge into `staging` and verify its branch checks.
4. Open a `staging` to `main` pull request. Review all differences, including
   teammates' changes, and wait for the required checks.
5. Merge into `main`. This can trigger production deployment.
6. Verify both deployments and record the deployed commit IDs and smoke checks.

The owner reports that the CI changes have merged into both branches and branch
rules have been created for `staging` and `main`. The requested policy is PRs and
passing CI without mandatory approving reviews. Exact saved rule options and
administrator bypass behavior remain unverified. Keep force pushes and branch
deletion disabled, and use teammate review for consequential changes.

## What GitHub Actions runs

Source: [CI workflow](.github/workflows/ci.yml).

Triggers: pushes to `main` or `staging`, and pull requests targeting either branch.
Workflow: `Campus Pilot CI`; job: `build-and-test`; runner: `ubuntu-latest`.

| Order | Check | Command or behavior |
| --- | --- | --- |
| 1 | Python setup | Python 3.13; pip download cache |
| 2 | Python dependencies | Upgrade pip; install `requirements-demo.txt` |
| 3 | Python unittest | `python -B -m unittest discover -s tests -v` |
| 4 | Python pytest | Install pytest; run `python -m pytest` |
| 5 | Node setup | Node 20; npm download cache using frontend lockfile |
| 6 | Frontend dependencies | `npm ci` in `frontend` |
| 7 | Frontend lint | `npm run lint` |
| 8 | Route types and TypeScript | `next typegen`, then `tsc --noEmit --incremental false` using local binaries |
| 9 | Frontend proxy tests | `node --test tests/ai-proxy.test.mjs` |
| 10 | Frontend production build | `npm run build` |

Steps run sequentially; failure blocks later steps. Next.js type generation must
precede TypeScript because `LayoutProps` is generated, not a built-in global.

Both Python test steps explicitly use `DATABASE_URL=sqlite:///:memory:`.
Tests also create temporary SQLite databases and inject mocked providers/fetch.
The workflow passes no OpenAI or Pinecone secrets. No live model calls or production
migrations are part of CI. The unittest and pytest steps overlap; consolidation is
a future improvement. Pytest is currently unpinned, and demo requirements do not
install Alembic, so migration coverage can skip when it is unavailable.

GitHub reports deprecated Node runtimes in the current action versions. Updating
actions is pending; this is distinct from the Node 20 runtime selected for frontend
commands. The frontend build downloads Google Fonts and needs network access.

## Environments and secrets

| Environment | Current state |
| --- | --- |
| Local | Root `.env` for backend configuration; ignored and not tracked by Git |
| CI | Fictional fixtures, mocked calls and temporary SQLite; no production secrets |
| Staging | Git branch exists; separate hosted backend/database not verified |
| Production backend | Render; owner confirmed branch `main` and Auto-Deploy set to After CI Checks Pass |
| Production frontend | Vercel; screenshot confirms production tracks `main` |

`staging` is a branch, not proof of an isolated hosted environment. Preview settings,
staging services and staging credentials still need verification.

Configuration names only:

- `DATABASE_URL`: backend environment / authorized root `.env`; required for shared
  database access and Alembic. Never put it in frontend code or `NEXT_PUBLIC_*`.
- `AI_API_KEY`: server-side provider key, only where approved live AI is enabled.
- `AI_MODEL`: model selection for the AI adapter when configured.
- `AI_API_BASE_URL`: Next.js server-side URL for the separate AI API. Defaults to
  loopback for local development; the main backend does not establish AI demo hosting.
- Other names in `.env.example` are templates, not evidence that their features or
  production integrations are implemented. In particular, `JWT_SECRET` alone does
  not implement authentication.

Never record secret values in this document, PRs, screenshots or logs. The owner
reports rotating the exposed database password and updating Supabase/Render/local
configuration. Rotation and access-log review were not independently audited.

## Hosting and deployment gates

### Render backend

Open the backend **service**, then Settings. Confirm the linked branch is `main`
and Auto-Deploy is **After CI Checks Pass**. The owner confirmed these settings.
Record the deployed commit from the service's deploy history and confirm it is Live.
Build/start commands and the exact deployed dependency manifest have not been
verified in this task; check the service settings before changing them.

### Vercel frontend

Settings > Environments > Production shows branch tracking `main`. The owner
confirmed the latest production deployment is Ready and matches the expected merge.
The homepage screenshot displayed departments successfully.

Vercel production branch tracking does not prove it waits for GitHub Actions after
a merge. No additional Vercel CI gate was verified. Required PR checks protect the
merge path when enforced; bypasses or direct pushes can defeat that protection.

Hosting integrations perform deployment; this workflow has no deployment job.
Do not add a second deployment mechanism without checking the existing integration.

## Verify a release

After every authorized release:

1. Confirm GitHub Actions is green for the intended commit/branch.
2. Record the backend and frontend deployment commit IDs, timestamps and statuses.
3. Open the frontend: <https://campus-pilot-kappa.vercel.app>.
4. Confirm the homepage loads and displays departments from the backend.
5. From Render's service dashboard, use its actual public URL plus `/departments`.
   Expect a successful JSON response with a `departments` array; an empty array is
   valid. Use the dashboard URL rather than relying on an old copied hostname.
6. A response from `/` only proves the app is running; it does not test a database
   query. A working homepage does not prove `/ai` or the real model works.
7. Review sanitized errors if a check fails. Avoid test writes to production.

The owner confirmed the production homepage, department display and expected Vercel
deployment. This is user-provided smoke-test evidence, not an automated live audit.

## Roll back a failed release

These are recovery instructions, not authorization to perform a production rollback.
Coordinate with Cassie and the affected application owner. No rollback was tested.

1. Record the failing commit, symptoms and detection time. Select a known-good
   deployment compatible with the current database schema and API contracts.
2. For Render, open the service deploy history and use the rollback option on the
   chosen successful deploy, subject to retained-artifact availability.
3. For Vercel, open Deployments and use Instant Rollback for an eligible prior
   production deployment. Availability depends on the project's plan and history.
4. Repeat the release checks above and record recovery time.
5. Fix or revert the offending source change through a PR so Git and the live app
   agree. Do not reset shared branches or force push.
6. Inspect auto-deploy/promotion settings after recovery before resuming releases;
   rollback can affect subsequent automatic deployment behavior.

Application rollback does not restore database contents or guarantee restoration
of environment settings. Never restore a compromised credential. Schema rollback,
database restore and backups need separate reviewed procedures with Brian/Cassie.
Do not run `alembic downgrade` blindly. Backup availability and restoration testing
remain unverified; automated production migrations are not enabled here.

## Verification history and remaining work

Local verification during CI implementation: 106 unittest tests and seven mocked
frontend tests passed; lint, TypeScript and production build passed. Python ran
locally on 3.15 rather than CI's 3.13; local pytest was unavailable. The type-generation
fix was checked locally and pushed as `ca40009`. Overall hosted run evidence should
be recorded with its actual run URL and commit; the cleanup screenshot alone does
not establish success for the entire job.

Remaining work: verify saved branch rules, Vercel deployment gating, separate staging
infrastructure, backup/restore readiness, action updates, dependency/secret scanning,
monitoring and a real timing/incident log. Add dates, CI/deployment links, commit IDs,
durations, failures and recovery times; do not invent metrics.

Brian's API authentication/authorization work remains separate. Database password
rotation and passing CI do not secure unrestricted CRUD endpoints. Public access,
CORS and error sanitization require their own review before production use.

## Provider references

- [GitHub protected branches](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches)
- [Render deploys and CI gating](https://render.com/docs/deploys)
- [Render rollback behavior](https://render.com/docs/rollbacks)
- [Vercel Instant Rollback](https://vercel.com/docs/instant-rollback)
