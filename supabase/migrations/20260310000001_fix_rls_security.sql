-- Migration: Remediate RLS security issues in accusations schema
-- Addresses:
--   1. ai_audit_run audit table exposed to anon (server-side only)
--   2. Redundant broad UPDATE grant on sessions overriding column-specific grant
--   3. Explicit service_role grant on evidence_full for clarity

-- =============================================================
-- 1. ai_audit_run: revoke anon access
-- Audit log is server-side troubleshooting data — never player-facing.
-- =============================================================

REVOKE SELECT ON accusations.ai_audit_run FROM anon;
DROP POLICY IF EXISTS audit_select ON accusations.ai_audit_run;

-- =============================================================
-- 2. sessions: fix authenticated UPDATE grant
-- Remove broad UPDATE so the column-specific GRANT UPDATE (state)
-- is meaningful. authenticated may only update the state column.
-- =============================================================

REVOKE UPDATE ON accusations.sessions FROM authenticated;
GRANT UPDATE (state) ON accusations.sessions TO authenticated;

-- =============================================================
-- 3. evidence_full: explicit service_role SELECT grant
-- service_role is a superuser in Supabase and already has access,
-- but this makes the intent explicit and guards against policy changes.
-- =============================================================

GRANT SELECT ON accusations.evidence_full TO service_role;
