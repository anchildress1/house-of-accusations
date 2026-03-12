# AGENTS.md — Supabase

Parent: [../AGENTS.md](../AGENTS.md)

## Project

All tables, views, and functions belong to the `accusations` schema in the
**supascribe-notes** Supabase project (ID: `stzewoyiciyxugwkxgwf`, region:
`us-east-1`).

The `public` schema is read-only from this project's perspective. Do not
create, alter, or drop any object in `public`.

## Migration Rules

- Migrations live in `supabase/migrations/` with timestamp-prefixed filenames
  (`YYYYMMDDHHMMSS_description.sql`)
- Migrations must **only** be applied to the supascribe-notes project after the
  changes have been successfully pushed to GitHub. Never apply a migration to
  the live database before the code is in the remote repository.
- All migrations target the `accusations` schema exclusively
- RLS must be enabled on every new table
- Anon role is read-only (`SELECT` only) — all write grants go to
  `authenticated` or are handled by `service_role`

## Applying Migrations

Use the Supabase MCP (`execute_sql`) or the Supabase dashboard to run
migrations against supascribe-notes. Confirm the branch/PR has been pushed
and CI is green before executing any SQL on the live project.
