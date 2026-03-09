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

-- Grant schema usage to anon and authenticated roles
GRANT USAGE ON SCHEMA accusations TO anon, authenticated;

-- Sessions: anon can create, read, and update state (state column only)
GRANT SELECT, INSERT ON accusations.sessions TO anon, authenticated;
GRANT UPDATE (state) ON accusations.sessions TO anon, authenticated;

CREATE POLICY sessions_select ON accusations.sessions
    FOR SELECT TO anon, authenticated
    USING (true);

CREATE POLICY sessions_insert ON accusations.sessions
    FOR INSERT TO anon, authenticated
    WITH CHECK (true);

CREATE POLICY sessions_update ON accusations.sessions
    FOR UPDATE TO anon, authenticated
    USING (true)
    WITH CHECK (true);

-- Evidence selections: anon can create and read
GRANT SELECT, INSERT ON accusations.evidence_selections TO anon, authenticated;

CREATE POLICY evidence_select ON accusations.evidence_selections
    FOR SELECT TO anon, authenticated
    USING (true);

CREATE POLICY evidence_insert ON accusations.evidence_selections
    FOR INSERT TO anon, authenticated
    WITH CHECK (true);

-- AI audit run: anon can create and read (append-only trail)
GRANT SELECT, INSERT ON accusations.ai_audit_run TO anon, authenticated;

CREATE POLICY audit_select ON accusations.ai_audit_run
    FOR SELECT TO anon, authenticated
    USING (true);

CREATE POLICY audit_insert ON accusations.ai_audit_run
    FOR INSERT TO anon, authenticated
    WITH CHECK (true);

-- Ensure the game role has NO write access to public schema
-- (public.cards is read-only from the game's perspective)
-- Note: Supabase default grants SELECT on public tables to anon.
-- No additional grants needed — we explicitly do NOT grant INSERT/UPDATE/DELETE.
