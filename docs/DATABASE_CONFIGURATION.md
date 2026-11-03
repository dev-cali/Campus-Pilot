# Backend database configuration

Set `DATABASE_URL` in the backend process environment before starting the API
or running Alembic. Both use the same value and fail if it is missing.
Use the connection string supplied by your database owner; percent-encode
special characters in its password. Never commit a real connection string.

`.env.example` lists the variable names only. These entry points do not
automatically load `.env`; configure environment variables through your shell
or hosting provider's secret settings. Keep database credentials server-side.

Previously committed database passwords must be rotated by the Supabase owner
and updated in each authorized deployment. Removing literals from source does
not revoke credentials or remove them from Git history.
