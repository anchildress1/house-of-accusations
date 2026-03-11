# PRD — House of Accusations

> Product Requirements Document reconstructed from AGENTS.md, codebase
> exploration, and stakeholder input. This is the living spec for v1.

## 1. Product Overview

House of Accusations is an interactive developer portfolio disguised as a
mansion investigation game. Players explore rooms in a 3×3 grid, evaluate
evidence cards drawn from a real project database, classify them as **Proof**
or **Objection**, and ultimately **Accuse** or **Pardon**. The session
produces a generated resume and cover letter from the evaluated artifacts.

**Target audience**: Hiring managers, recruiters, and technical leads visiting
the portfolio.

**Core value prop**: A memorable, gamified alternative to a static resume that
demonstrates technical depth through interactive storytelling.

## 2. The Auditor (AI Character)

The Auditor is the in-game AI narrator and evaluator. It guides players with
theatrical, accusatory flair — think Clue board game, not courtroom.

### Personality

- Dramatic, slightly smug, always watching
- Observes and reacts but **never assists** or hints at "correct" answers
- Writes the final cover letter in its own voice
- v1: Single consistent tone throughout
- v2 (deferred): Phase-based tone shifts (early/mid/late/final)

### Technical Behavior

- Each card classification triggers **one LLM call** producing:
  1. **Score** (float, −1.0 to 1.0): `< 0` = Objection, `≥ 0` = Proof
  2. **Narrative reaction**: short dramatic line in The Auditor's voice
- All output written to `accusations.ai_audit_run` before client response
- Audit trail is for troubleshooting only — not surfaced in any UI

## 3. Game Mechanics

### 3.1 Room Map (3×3 Grid)

```
Hidden Attic  |  Gallery      |  Control Room
Parlor        |  Entry Hall   |  Library
Workshop      |  Lower Cellar |  Back Hall
```

### 3.2 Room → Category Mapping

| Room | Category | Notes |
|------|----------|-------|
| Hidden Attic | About | Landing/tutorial room |
| Gallery | Awards | |
| Workshop | Experimentation | |
| Control Room | Decisions | |
| Parlor | Work Style | |
| Library | Philosophy | |
| Back Hall | Experience | |
| Lower Cellar | Challenges | |
| Entry Hall | *(disabled)* | Non-interactive, atmospheric center |

### 3.3 Board View

- All views render as overlays on room background images (`public/`)
- Navigation uses a 3×3 invisible hotspot grid over the mansion exterior
- Hotspot coordinates are percentage-based, independent of artwork resolution
- Clicking a hotspot opens the corresponding room overlay
- Center cell (Entry Hall) is non-interactive

### 3.4 Room View

1. 6 cards drawn randomly from the room's category
2. Query: `SELECT * FROM public.cards WHERE category = :room AND signal > 2 AND "objectID" NOT IN (:consumed_ids) ORDER BY random() LIMIT 6`
3. Player selects 1 card → card moves to center, title + blurb visible
4. Player classifies: **Proof** or **Objection** (permanent, no undo)
5. The Auditor reacts with a single line
6. Card stored as evidence; player returns to mansion

### 3.5 Deck Behavior

- Selected cards never reappear in any future draw
- Shown-but-not-selected cards are disabled until no fresh cards remain
- When all eligible cards have been shown, disabled cards reactivate and
  the deck reshuffles

### 3.6 Streak

- Display-only metric in the UI overlay
- Player's classification vs. The Auditor's score direction:
  - Match → streak increments
  - Mismatch → streak resets to 0
- Does **not** affect gameplay, scoring, or final outcome

### 3.7 Session State Machine

```
created → exploring → deciding → resolved
```

| State | Trigger | Description |
|-------|---------|-------------|
| `created` | Session initialized | No room entered yet |
| `exploring` | First room entered | Navigating rooms, classifying evidence |
| `deciding` | ≥ 1 classification | Accuse/Pardon button enabled |
| `resolved` | Final decision made | Session complete, no further actions |

### 3.8 Accusation Text

- v1: Selected from a static list at session start
- v2 (deferred): AI-generated from card corpus

### 3.9 Final Decision

1. Player chooses **Accuse** or **Pardon**
2. The Auditor evaluates the decision against all collected evidence
3. Session transitions to `resolved`

## 4. Final Output

Upon session resolution, three artifacts are generated:

1. **Resume** — fixed HTML template populated with Proof-classified artifacts.
   Real-world resume format (stakeholder will provide template copy).
2. **Cover Letter** — single-page narrative (2–3 paragraphs max) written by
   The Auditor using collected evidence. Length scales with how much the
   player explored — a player who classified 2 cards gets a shorter letter
   than one who classified 15. Reflects the Accuse/Pardon decision and the
   strength of the case built.
3. **Session Summary** — all evaluated artifacts, classifications, and scores

## 5. Data Model

### 5.1 Read-Only Source: `public.cards`

| Column | Type | Player Visible? |
|--------|------|-----------------|
| `objectID` | uuid (PK) | No |
| `title` | text | Yes |
| `blurb` | text | Yes |
| `fact` | text | **No** (hidden until final reveal) |
| `category` | text | Indirectly (maps to room) |
| `signal` | smallint (1–5) | No |
| `url` | text (nullable) | No |
| `tags` | jsonb | No (ignored v1) |
| `projects` | text[] | No (ignored v1) |
| `created_at` / `updated_at` / `deleted_at` | timestamptz | No |

### 5.2 Game Tables: `accusations` Schema

**`accusations.sessions`**

| Column | Type | Notes |
|--------|------|-------|
| `session_id` | uuid (PK) | `gen_random_uuid()` |
| `state` | `accusations.session_state` enum | created/exploring/deciding/resolved |
| `accusation_text` | text | Static list v1 |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | Auto-trigger |

**`accusations.evidence_selections`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | bigint (PK) | Serial |
| `session_id` | uuid (FK → sessions) | |
| `card_id` | uuid (FK → public.cards.objectID) | |
| `user_position` | `accusations.user_position` enum | proof/objection |
| `ai_score` | numeric(3,2) | −1.0 to 1.0 |
| `room` | text | Category/room where selected |
| `created_at` | timestamptz | |

**`accusations.ai_audit_run`**

| Column | Type | Notes |
|--------|------|-------|
| `id` | bigint (PK) | Serial |
| `session_id` | uuid (FK → sessions) | |
| `chosen_card_id` | uuid (FK → public.cards.objectID) | |
| `user_position` | `accusations.user_position` enum | |
| `contract_name` | text | AI contract identifier |
| `contract_version` | text | |
| `final_score` | numeric(3,2) | |
| `raw_output_text` | text | Full LLM response |
| `created_at` | timestamptz | |

### 5.3 Views

- **`accusations.evidence_index`** — Player-facing: joins cards with
  selections, hides `fact` column
- **`accusations.evidence_full`** — AI/service-role only: includes `fact`,
  revoked from anon/authenticated

## 6. Architecture

### 6.1 Stack

| Layer | Technology |
|-------|------------|
| Frontend | SvelteKit (Svelte 5, Vite 6, Node 22) |
| Backend | FastAPI (Python 3.13) |
| AI | Anthropic Python SDK (Claude) |
| Database | Supabase (PostgreSQL) — `supascribe-notes` project |
| Deploy | Cloud Run (2 services: `web` + `api`) |

### 6.2 Service Boundaries

```
┌─────────────┐     HTTP/JSON     ┌─────────────┐     Supabase Client
│  SvelteKit  │ ──────────────►  │   FastAPI    │ ──────────────────►  Supabase
│  (web)      │                   │   (api)      │ ──► Anthropic SDK
└─────────────┘                   └─────────────┘
```

- Frontend calls API endpoints (no direct Supabase access from browser)
- API uses `anon` client for reads, `service_role` for writes
- AI calls happen server-side only

### 6.3 Deployment

| Service | Cloud Run Service | Domain |
|---------|-------------------|--------|
| Frontend (web) | TBD | `unstable-accusations.anchildress1.dev` |
| Backend (api) | TBD | `unstable-accusations-api.anchildress1.dev` |

- Net new Cloud Run setup — no existing config
- Service accounts needed for both services
- Dockerfiles exist in `web/` and `api/`

### 6.4 CORS

Allowed origins: `localhost:5173`, `localhost:4173`,
`https://unstable-accusations.anchildress1.dev`

## 7. API Endpoints

### 7.1 Implemented

| Method | Path | Description | Status |
|--------|------|-------------|--------|
| `GET` | `/health` | Health check | ✅ Done |
| `POST` | `/sessions` | Create new session | ✅ Done |
| `GET` | `/sessions/{id}` | Get session by ID | ✅ Done |
| `PATCH` | `/sessions/{id}/state` | Advance session state | ✅ Done |

### 7.2 Planned (Not Yet Implemented)

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/sessions/{id}/cards?room=` | Draw 6 cards for a room |
| `POST` | `/sessions/{id}/evidence` | Classify a card (triggers AI eval) |
| `GET` | `/sessions/{id}/evidence` | List classified evidence |
| `POST` | `/sessions/{id}/decide` | Submit Accuse/Pardon |
| `GET` | `/sessions/{id}/results` | Get resume + cover letter + summary |

## 8. Frontend Views

### 8.1 Visual Design

**Aesthetic**: Steampunk Mansion — modern UI with glassmorphism effects over
dark, atmospheric backgrounds. Not a literal drop-in of the palette; the
colors inform the design system while maintaining contemporary glass/blur
treatments.

**Color Palette** (Steampunk Mansion Blue-Gold):

| Token | Name | Hex | Usage |
|-------|------|-----|-------|
| `--night` | Night | `#0F1013` | Primary background, deepest dark |
| `--walnut` | Walnut | `#1F1812` | Card backs, secondary dark surfaces |
| `--shadow-brown` | Shadow Brown | `#2B2119` | Elevated dark surfaces |
| `--midnight-blue` | Midnight Blue | `#121A26` | Glass overlay tint |
| `--prussian-blue` | Prussian Blue | `#1A2A3A` | Panel backgrounds |
| `--steel-blue` | Steel Blue Accent | `#4A6A8A` | Interactive elements, borders |
| `--parchment` | Parchment | `#ECE6D8` | Card faces, light surfaces |
| `--mist` | Mist Text | `#F3F3F2` | Primary text on dark |
| `--antique-gold` | Antique Gold | `#D4B06A` | Headings, emphasis, Proof accent |
| `--warm-brass` | Warm Brass | `#B8924E` | Secondary gold, borders |
| `--dark-brass` | Dark Brass | `#7A5A2A` | Muted gold, disabled states |
| `--highlight-glint` | Highlight Glint | `#F0D9A0` | Hover states, active highlights |
| `--danger-burgundy` | Danger Burgundy | `#7B2E2E` | Objection accent, warnings |

**Responsive**: Desktop-first, but must be responsive (no mobile-specific
optimizations in v1).

### 8.2 Views (Not Yet Implemented)

| View | Description | Notes |
|------|-------------|-------|
| **Mansion Board** | 3×3 grid over exterior background, hotspot navigation | |
| **Room Overlay** | 6 cards displayed, select → classify flow | |
| **Evidence Drawer** | Toggleable overlay showing classified evidence by type | Player toggles open/closed |
| **Decision View** | Accuse/Pardon prompt with evidence summary | |
| **Results View** | Resume, cover letter, session summary | |
| **Tutorial/About** | Hidden Attic — purely narrative onboarding, no cards | Introduces The Auditor and rules |

## 9. Non-Functional Requirements

### 9.1 Accessibility

- Full keyboard navigation (board, room, results)
- Focus management on view transitions
- `prefers-reduced-motion` support
- Semantic HTML + ARIA attributes
- Screen reader support for card content and classifications

### 9.2 Performance

- Lighthouse audits must pass
- Lazy load room backgrounds
- Minimize JS bundle size
- API responses < 200ms for non-AI endpoints
- Performance test suite for critical paths

### 9.3 Security

- No secrets in source control
- Supabase RLS on all tables
- Input validation via Pydantic models
- CORS restricted to known origins
- No raw SQL — parameterized queries only
- OWASP top 10 awareness

### 9.4 Testing

- All backend endpoints must have tests
- All frontend components must have tests
- Integration tests for full game loop
- Performance tests for API + frontend rendering
- Coverage ≥ 85% enforced

### 9.5 Code Quality

- SonarQube on all PRs (no regressions)
- Conventional commits + RAI footer
- Lefthook pre-commit hooks enforced
- `ruff check` + `mypy --strict` (API)
- `eslint` + `svelte-check` (web)

## 10. Implementation Status

### ✅ Complete

- [x] Repository scaffolding (Makefile, lefthook, CI/CD, Dockerfiles)
- [x] Supabase schema (`accusations` schema with 3 tables)
- [x] Database views (evidence_index, evidence_full)
- [x] RLS policies (anon read-only, service_role writes)
- [x] Session CRUD + state machine endpoints
- [x] Session endpoint tests (100% coverage)
- [x] Room background images (10 JPGs in `public/`)
- [x] SonarQube integration
- [x] SvelteKit project scaffolded (no routes yet)

### 🔲 Remaining (v1)

- [ ] Card draw endpoint
- [ ] Evidence classification endpoint (with AI evaluation)
- [ ] Evidence retrieval endpoint
- [ ] Final decision endpoint (Accuse/Pardon)
- [ ] Results generation endpoint (resume + cover letter)
- [ ] AI contract/prompt for The Auditor
- [ ] Static accusation text list
- [ ] Mansion board view (3×3 hotspot grid)
- [ ] Room overlay view (card display + classification)
- [ ] Evidence drawer UI
- [ ] Decision view UI
- [ ] Results view UI (resume + cover letter + summary)
- [ ] Tutorial/About room (Hidden Attic)
- [ ] Streak display
- [ ] Keyboard navigation
- [ ] Accessibility audit
- [ ] Lighthouse performance pass
- [ ] E2E tests (full game loop)
- [ ] Cloud Run deployment config

### 🚫 v2 Deferred

- Room cooldown mechanics
- Narrative phase thresholds (tone shifts)
- Session replay from stored session_id
- AI-generated accusation text

## 11. Resolved Questions

| # | Question | Answer |
|---|----------|--------|
| 1 | API endpoint design | Confirmed as specified in §7.2 |
| 2 | Visual style | Steampunk Mansion — glassmorphism + blue-gold palette (§8.1) |
| 3 | Evidence drawer | Toggleable overlay |
| 4 | Tutorial room (Hidden Attic) | Purely narrative onboarding, no cards |
| 5 | Mobile support | Desktop-first, responsive but no mobile-specific work |
| 6 | Static accusation list | Stakeholder will draft (blocker for full session flow) |
| 7 | Resume template | Real-world format; stakeholder will provide copy (blocker for results view) |
| 8 | Cover letter length | Single page, 2–3 paragraphs, scales with play depth |
| 9 | Card `tags`/`projects` columns | Ignored for v1 |
| 10 | Deployment | Net new Cloud Run; needs service accounts |
| 11 | Domain routing | Subdomain: `unstable-accusations-api.anchildress1.dev` |

## 12. Remaining Blockers

> These items must be provided before the dependent work can ship.

| Blocker | Blocks | Owner |
|---------|--------|-------|
| Static accusation text list | Full session flow (accusation_text on session create) | Stakeholder |
| Resume template copy | Results view implementation | Stakeholder |

---

*Last updated: 2026-03-10*
