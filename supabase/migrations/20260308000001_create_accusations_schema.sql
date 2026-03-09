-- Migration: Create accusations schema for House of Accusations gameplay
-- Tables: sessions, evidence_selections, ai_audit_run
-- Includes indexes and RLS policies

-- =============================================================
-- Schema
-- =============================================================

CREATE SCHEMA IF NOT EXISTS accusations;

-- =============================================================
-- Enums
-- =============================================================

CREATE TYPE accusations.session_state AS ENUM (
    'created',
    'exploring',
    'deciding',
    'resolved'
);

CREATE TYPE accusations.user_position AS ENUM (
    'proof',
    'objection'
);

-- =============================================================
-- Table: sessions
-- =============================================================

CREATE TABLE accusations.sessions (
    session_id   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    state        accusations.session_state NOT NULL DEFAULT 'created',
    accusation_text text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

COMMENT ON TABLE accusations.sessions IS 'Game sessions tracking state machine: created → exploring → deciding → resolved';

-- =============================================================
-- Table: evidence_selections
-- =============================================================

CREATE TABLE accusations.evidence_selections (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id   uuid NOT NULL REFERENCES accusations.sessions(session_id),
    card_id      uuid NOT NULL,
    user_position accusations.user_position NOT NULL,
    ai_score     numeric(4,2) NOT NULL CHECK (ai_score >= -1.0 AND ai_score <= 1.0),
    room         text NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_card FOREIGN KEY (card_id) REFERENCES public.cards("objectID")
);

COMMENT ON TABLE accusations.evidence_selections IS 'Player evidence classifications: each card picked and classified as proof or objection';

-- =============================================================
-- Table: ai_audit_run
-- =============================================================

CREATE TABLE accusations.ai_audit_run (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id       uuid NOT NULL REFERENCES accusations.sessions(session_id),
    chosen_card_id   uuid NOT NULL,
    user_position    accusations.user_position NOT NULL,
    contract_name    text NOT NULL,
    contract_version text NOT NULL,
    final_score      numeric(4,2) NOT NULL CHECK (final_score >= -1.0 AND final_score <= 1.0),
    raw_output_text  text NOT NULL,
    created_at       timestamptz NOT NULL DEFAULT now(),

    CONSTRAINT fk_audit_card FOREIGN KEY (chosen_card_id) REFERENCES public.cards("objectID")
);

COMMENT ON TABLE accusations.ai_audit_run IS 'AI evaluation audit trail for troubleshooting — not surfaced in any UI';

-- =============================================================
-- Indexes
-- =============================================================

-- Sessions: filter by state for active session lookups
CREATE INDEX idx_sessions_state ON accusations.sessions(state);

-- Evidence: look up all evidence for a session, ordered by creation
CREATE INDEX idx_evidence_session_id ON accusations.evidence_selections(session_id, created_at);

-- Evidence: check which cards have been consumed in a session
CREATE INDEX idx_evidence_card_session ON accusations.evidence_selections(session_id, card_id);

-- Audit: look up audit runs for a session
CREATE INDEX idx_audit_session_id ON accusations.ai_audit_run(session_id, created_at);

-- =============================================================
-- Updated_at trigger (sessions only — other tables are append-only)
-- =============================================================

CREATE OR REPLACE FUNCTION accusations.set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_sessions_updated_at
    BEFORE UPDATE ON accusations.sessions
    FOR EACH ROW
    EXECUTE FUNCTION accusations.set_updated_at();

-- =============================================================
-- Row-Level Security
-- =============================================================

-- Enable RLS on all tables
ALTER TABLE accusations.sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE accusations.evidence_selections ENABLE ROW LEVEL SECURITY;
ALTER TABLE accusations.ai_audit_run ENABLE ROW LEVEL SECURITY;

-- Grant schema usage to anon (read-only) and authenticated roles
GRANT USAGE ON SCHEMA accusations TO anon, authenticated;

-- =============================================================
-- Anon role: READ-ONLY access to all tables
-- All write operations go through the backend API using service_role
-- (which bypasses RLS). Anon must never insert/update/delete.
-- =============================================================

-- Sessions: anon can only read
GRANT SELECT ON accusations.sessions TO anon;

CREATE POLICY sessions_select ON accusations.sessions
    FOR SELECT TO anon
    USING (true);

-- Evidence selections: anon can only read
GRANT SELECT ON accusations.evidence_selections TO anon;

CREATE POLICY evidence_select ON accusations.evidence_selections
    FOR SELECT TO anon
    USING (true);

-- AI audit run: anon can only read
GRANT SELECT ON accusations.ai_audit_run TO anon;

CREATE POLICY audit_select ON accusations.ai_audit_run
    FOR SELECT TO anon
    USING (true);

-- =============================================================
-- Authenticated role: full read/write access (for backend API key)
-- =============================================================

GRANT SELECT, INSERT, UPDATE ON accusations.sessions TO authenticated;
GRANT UPDATE (state) ON accusations.sessions TO authenticated;

CREATE POLICY sessions_insert ON accusations.sessions
    FOR INSERT TO authenticated
    WITH CHECK (true);

CREATE POLICY sessions_update ON accusations.sessions
    FOR UPDATE TO authenticated
    USING (true)
    WITH CHECK (true);

GRANT SELECT, INSERT ON accusations.evidence_selections TO authenticated;

CREATE POLICY evidence_insert ON accusations.evidence_selections
    FOR INSERT TO authenticated
    WITH CHECK (true);

GRANT SELECT, INSERT ON accusations.ai_audit_run TO authenticated;

CREATE POLICY audit_insert ON accusations.ai_audit_run
    FOR INSERT TO authenticated
    WITH CHECK (true);

-- Ensure no write access to public schema from game roles
-- (public.cards is read-only from the game's perspective)
-- Note: Supabase default grants SELECT on public tables to anon.
-- service_role bypasses RLS for all write operations.
