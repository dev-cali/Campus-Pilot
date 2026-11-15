# API authentication and authorization

Last reviewed: November 5, 2026 (Asia/Manila).

This document describes what the backend enforces today. It was written from
the source in `auth.py`, `main.py` and `routers/`, and the checks in
`tests/test_auth.py`. It is not a report on a hosted Supabase project.

## Division of responsibility

| Layer | Owns |
| --- | --- |
| Supabase Auth | Accounts, passwords, Google/Facebook sign-in, email verification, password reset, token issuance and refresh |
| `auth.py` (this API) | Verifying the access token, linking it to a local `users` row, and deciding what that role may do |

The API verifies tokens **locally** with the project's JWT secret, so an
authenticated request does not call Supabase and does not fail when Supabase is
unreachable. Supabase availability only affects signing in, not using an
already-issued token.

## Configuration

| Variable | Required | Purpose |
| --- | --- | --- |
| `SUPABASE_JWT_SECRET` | yes for protected routes | Project JWT secret used to verify tokens (HS256) |
| `SUPABASE_JWT_ISSUER` | no | Expected `iss` claim, e.g. `https://<project-ref>.supabase.co/auth/v1`; checked only when set |
| `ALLOWED_ORIGINS` | no | Comma-separated frontend origins for CORS; defaults to `http://localhost:3000` |

`.env.example` lists the names with placeholder values. Never commit real
values. If `SUPABASE_JWT_SECRET` is missing, protected routes answer **503**;
they never fall back to anonymous access.

## Token contract

The frontend sends the Supabase access token as a bearer token:

```
Authorization: Bearer <supabase access token>
```

`auth.py` accepts a token only when all of these hold:

- algorithm is HS256 (the token's own `alg` header cannot switch it)
- signature matches `SUPABASE_JWT_SECRET`
- `exp` is present and in the future
- `sub` and `aud` are present; `aud` is `authenticated`
- `iss` matches `SUPABASE_JWT_ISSUER` when that variable is set
- the verified `email` claim matches a row in `users` (case-insensitive)

Anything else is a **401** with `WWW-Authenticate: Bearer`. The response does
not distinguish an expired token from a forged one.

### Roles

Authorization uses `users.role`, not the token. The Supabase `role` claim is the
Postgres role (`authenticated`) and says nothing about CampusPilot permissions.

| `users.role` | Meaning |
| --- | --- |
| `student` | Read reference data and documents; may record questions against their own account |
| `staff` or `admin` | Everything a student can do, plus create/update/delete records and use `/test-ai` |

Comparison is case-insensitive and ignores surrounding whitespace.

## Access matrix

| Endpoint | Anonymous | Student | Staff/Admin |
| --- | --- | --- | --- |
| `GET /` | 200 | 200 | 200 |
| `GET /departments` | 401 | 200 | 200 |
| `GET /documents`, `GET /documents/{id}` | 401 | 200 | 200 |
| `POST/PUT/DELETE /documents` | 401 | 403 | allowed |
| `GET /chunks`, `GET /chunks/{id}` | 401 | 200 | 200 |
| `POST/DELETE /chunks` | 401 | 403 | allowed |
| `POST /ingest/chunk` | 401 | 403 | allowed |
| `GET /users`, `GET /users/{id}` | 401 | 403 | 200 |
| `POST/DELETE /users` | 401 | 403 | allowed |
| `GET /questions`, `GET /questions/{id}` | 401 | 403 | 200 |
| `POST /questions` | 401 | 200, forced to own `user_id` | 200, may target another user |
| `DELETE /questions/{id}` | 401 | 403 | allowed |
| `GET /test-ai` | 401 | 403 | allowed |

`GET /` stays public on purpose: it is a liveness probe that exposes no data.

`ai/demo_api.py` is a separate, loopback-only fictional demo and is not covered
by these rules; it does not import `main.py` or `database.py`.

## Error behaviour

| Situation | Status | Body |
| --- | --- | --- |
| No token / bad token | 401 | `detail` naming the problem in general terms |
| Valid token, no matching `users` row | 401 | "No CampusPilot account matches this identity." |
| Valid token, role too low | 403 | "This action requires a staff account." |
| `SUPABASE_JWT_SECRET` unset | 503 | "Authentication is not configured on this server." |
| `/test-ai` provider failure | 503 | neutral message; the real error is logged, never returned |

## Local development

1. Set `SUPABASE_JWT_SECRET` from the Supabase project settings (Dashboard >
   Project Settings > API > JWT Settings). Use the legacy JWT secret while the
   project signs with HS256.
2. Sign in through the frontend (or `supabase-js`) and copy the access token.
3. Send it as `Authorization: Bearer ...` to the API.

No hosted project was verified while writing this; if the project uses the
newer asymmetric signing keys, `auth.py` needs JWKS support before real tokens
will verify (see below).

## Tests

`tests/test_auth.py` covers missing, malformed, expired, forged and unsigned
tokens, wrong audience, missing `exp`, unknown identities, every role boundary,
the fail-closed path, `/test-ai` ordering and sanitization, and CORS behaviour.
All of it runs offline: tokens are minted with a throwaway test secret.

`tests/test_backend_crud.py` overrides `get_current_user` with a staff principal
so CRUD behaviour stays covered without depending on tokens.

## Known gaps (deliberate, in priority order)

1. **No `/users/me`** and no per-user question history, so students cannot read
   their own records yet.
2. **Email is the identity link.** Teachers/support staff can change an email in
   Supabase and break the link. A nullable unique `supabase_user_id` column is
   the durable fix, once a baseline migration exists.
3. **Staff can create admin accounts** and delete other staff. Admin-only user
   management is not separated yet.
4. **`POST /questions` trusts `user_id` from staff callers.** Fine while staff
   are trusted; do not widen it carelessly.
5. **No asymmetric-key (JWKS) verification.** Needed if Supabase rotates the
   project to the newer signing keys.
6. **No rate limiting or request logging** on authentication failures.
7. **CORS is origin-restricted but not deployment-verified.** Set
   `ALLOWED_ORIGINS` to the Vercel production URL before release.
8. **`utils/supabase_client.py` is dead code.** Nothing imports it, and it falls
   back to the public anon key. Either delete it or restrict it to server-side
   use with the service-role key; do not leave it as a tempting shortcut.
