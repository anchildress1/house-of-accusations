# Data Model — House of Accusations

## Schema Overview

Two PostgreSQL schemas in the `supascribe-notes` Supabase project:

- **`public`** — Existing card corpus (read-only from the game)
- **`accusations`** — Game session data (created by migration `20260308000001`)

## Entity Relationship Diagram

```mermaid
erDiagram
    public_cards {
        uuid objectID PK
        text title UK
        text blurb UK
        text fact UK "hidden until reveal"
        text category
        smallint signal "1-5"
        text url
        jsonb tags
        text[] projects
        timestamptz created_at
        timestamptz updated_at
        timestamptz deleted_at "soft delete"
    }

    accusations_sessions {
        uuid session_id PK
        session_state state "created|exploring|deciding|resolved"
        text accusation_text "nullable"
        timestamptz created_at
        timestamptz updated_at
    }

    accusations_evidence_selections {
        uuid id PK
        uuid session_id FK
        uuid card_id FK
        user_position user_position "proof|objection"
        numeric ai_score "-1.0 to 1.0"
        text room
        timestamptz created_at
    }

    accusations_ai_audit_run {
        uuid id PK
        uuid session_id FK
        uuid chosen_card_id FK
        user_position user_position "proof|objection"
        text contract_name
        text contract_version
        numeric final_score "-1.0 to 1.0"
        text raw_output_text
        timestamptz created_at
    }

    accusations_sessions ||--o{ accusations_evidence_selections : "has evidence"
    accusations_sessions ||--o{ accusations_ai_audit_run : "has audits"
    public_cards ||--o{ accusations_evidence_selections : "referenced by"
    public_cards ||--o{ accusations_ai_audit_run : "evaluated in"
```

## Session State Machine

```mermaid
stateDiagram-v2
    [*] --> created : Session initialized
    created --> exploring : First room entered
    exploring --> deciding : At least 1 classification made
    deciding --> resolved : Accuse or Pardon
    resolved --> [*] : Session complete
```

## RLS Policy Summary

| Table | SELECT | INSERT | UPDATE | DELETE |
|-------|--------|--------|--------|--------|
| `public.cards` | anon (default) | — | — | — |
| `accusations.sessions` | anon | anon | anon | — |
| `accusations.evidence_selections` | anon | anon | — | — |
| `accusations.ai_audit_run` | anon | anon | — | — |

All policies use `USING (true)` / `WITH CHECK (true)` — no authentication
required (public portfolio experience).

## Evidence Views

Two database views provide the card query surface:

```mermaid
graph LR
    subgraph "public schema (read-only)"
        cards["public.cards<br/>276 cards"]
    end

    subgraph "accusations schema"
        idx["evidence_index<br/>(player-facing)"]
        full["evidence_full<br/>(AI-only)"]
    end

    cards --> idx
    cards --> full

    idx -.- note1["Excludes: fact column<br/>Filters: signal > 2, not deleted<br/>Access: anon, authenticated"]
    full -.- note2["Includes: fact column<br/>Filters: signal > 2, not deleted<br/>Access: authenticated only (no anon)"]
```

| View | `fact` visible | Access | Purpose |
|------|---------------|--------|---------|
| `accusations.evidence_index` | No | anon, authenticated | Player card draws |
| `accusations.evidence_full` | Yes | authenticated only | Auditor AI evaluation |

## Card Query Pattern

Player-facing queries use `evidence_index`:

```sql
SELECT "objectID", title, blurb, category, signal, url, tags
FROM accusations.evidence_index
WHERE category = :room
  AND "objectID" NOT IN (:consumed_ids)
ORDER BY random()
LIMIT 6;
```

AI evaluation queries use `evidence_full` (server-side only):

```sql
SELECT "objectID", title, blurb, fact, category, signal, url, tags
FROM accusations.evidence_full
WHERE "objectID" = :card_id;
```

Note: `fact` column is excluded from player-facing queries — visible only to
The Auditor and at final reveal.
