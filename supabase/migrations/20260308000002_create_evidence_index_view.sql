-- Migration: Create evidence index view over public.cards
-- Provides the player-facing card query surface with fact column excluded
-- and only eligible cards (signal > 2, not soft-deleted) exposed.

-- =============================================================
-- View: accusations.evidence_index
-- =============================================================
-- Player-facing view of eligible cards. Excludes:
--   - fact column (hidden until final reveal)
--   - cards with signal <= 2 (below relevance threshold)
--   - soft-deleted cards (deleted_at IS NOT NULL)

CREATE OR REPLACE VIEW accusations.evidence_index AS
SELECT
    "objectID",
    title,
    blurb,
    category,
    signal,
    url,
    tags
FROM public.cards
WHERE signal > 2
  AND deleted_at IS NULL;

COMMENT ON VIEW accusations.evidence_index IS
    'Player-facing card index: eligible cards with fact column hidden. '
    'Filter by category and exclude consumed card IDs at query time.';

-- Grant read-only access to the view
GRANT SELECT ON accusations.evidence_index TO anon, authenticated;

-- =============================================================
-- View: accusations.evidence_full
-- =============================================================
-- AI-only view that includes the fact column for Auditor evaluation.
-- Used server-side only — never exposed to PostgREST / client.

CREATE OR REPLACE VIEW accusations.evidence_full AS
SELECT
    "objectID",
    title,
    blurb,
    fact,
    category,
    signal,
    url,
    tags
FROM public.cards
WHERE signal > 2
  AND deleted_at IS NULL;

COMMENT ON VIEW accusations.evidence_full IS
    'Server-side card view including fact column for AI Auditor evaluation. '
    'Must never be exposed via PostgREST or client-facing APIs.';

-- Only service_role can access the full view (not anon)
GRANT SELECT ON accusations.evidence_full TO authenticated;
-- Explicitly revoke anon access to the full view
REVOKE ALL ON accusations.evidence_full FROM anon;
