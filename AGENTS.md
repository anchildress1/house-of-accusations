# AGENTS.md — House of Accusations

Source of truth: [Monday Board](https://anchildress1s-team.monday.com/boards/18401136576)

## Project Identity

House of Accusations is an interactive developer portfolio disguised as a
mansion investigation game. Players explore rooms, evaluate evidence cards,
classify them as Proof or Objection, and ultimately Accuse or Pardon. The
session produces a generated resume and cover letter from the evaluated
artifacts.

The Auditor is the in-game AI character. It guides players with theatrical,
accusatory flair — think Clue board game, not courtroom. The Auditor observes,
comments, and challenges but never assists. Its voice is dramatic, slightly
smug, and always watching.

## Stack

| Layer | Technology |
|-------|------------|
| Frontend | SvelteKit |
| Backend | FastAPI (Python) |
| AI SDK | Anthropic Python SDK (Claude) |
| Database | Supabase (PostgreSQL) — `supascribe-notes` project |
| Deploy | Cloud Run (2 services: web + api) |

## Repository Structure

```
house-of-accusations/
├── web/               # SvelteKit app
├── api/               # FastAPI app
├── supabase/          # Migrations, seed data, CLI/MCP instructions
│   └── migrations/
├── public/            # Static assets (background images, artwork)
├── .env               # Local secrets (NEVER committed)
├── .env.example       # Env var reference
├── AGENTS.md          # This file
├── Makefile           # Dev commands
└── lefthook.yml       # Git hooks (rai-lint, linting, tests)
```

## Database Architecture

All data lives in the `supascribe-notes` Supabase project under two schemas:

- **`public`** — existing cards table (276 cards). Read-only from the game's
  perspective. Schema must not be modified.
- **`accusations`** — game tables: sessions, audit runs, evidence selections.
  Separate RLS role with no write access to `public`.

### `public.cards` Schema (read-only, do not modify)

| Column | Type | Notes |
|--------|------|-------|
| `objectID` | uuid (PK) | `gen_random_uuid()` default |
| `title` | text | Unique, visible to player |
| `blurb` | text | Unique, visible to player |
| `fact` | text | Unique, hidden until final reveal |
| `category` | text | Maps to room categories |
| `signal` | smallint | 1–5, CHECK constraint |
| `url` | text | Nullable |
| `tags` | jsonb | Default `{}` |
| `projects` | text[] | Default `{}` |
| `created_at` | timestamptz | |
| `updated_at` | timestamptz | |
| `deleted_at` | timestamptz | Nullable (soft delete) |

Related tables (read-only): `public.card_revisions`, `public.generation_runs`.

### Card Access Rules

- Cards come from `public.cards` where `category = :room AND signal > 2`,
  excluding cards already consumed in the current session
- Use existing column names as-is. Do not rename columns.
- The `fact` column is hidden from the player until the final reveal.
- The Auditor sees `fact` immediately upon card draw.
- Card query pattern:
  ```sql
  SELECT * FROM public.cards
  WHERE category = :room AND signal > 2
    AND "objectID" NOT IN (:consumed_ids)
  ORDER BY random() LIMIT 6
  ```

### `accusations` Schema (game tables)

Tables to be defined via migrations in `supabase/migrations/`. Separate RLS
role with no write access to `public`. Core tables:

- **`accusations.sessions`** — session_id (PK), state (enum), accusation_text,
  created_at, updated_at
- **`accusations.evidence_selections`** — id, session_id (FK), card_id (FK to
  `public.cards.objectID`), user_position (proof/objection), ai_score, room,
  created_at
- **`accusations.ai_audit_run`** — id, session_id (FK), chosen_card_id,
  user_position, contract_name, contract_version, final_score,
  raw_output_text, created_at

Exact DDL will be designed during implementation. All tables require RLS
policies.

### Audit Storage

Evaluation results are written to `accusations.ai_audit_run` before the
client response is sent. This is a **DB insert trail for manual
troubleshooting only** — not exposed in any player-facing or admin UI.

## Game Rules

### Room Map (3x3 Grid)

```
Hidden Attic  |  Gallery      |  Control Room
Parlor        |  Entry Hall   |  Library
Workshop      |  Lower Cellar |  Back Hall
```

### Room Categories

| Room | Category |
|------|----------|
| Hidden Attic | About (landing/tutorial room) |
| Gallery | Awards |
| Workshop | Experimentation |
| Control Room | Decisions |
| Parlor | Work Style |
| Library | Philosophy |
| Back Hall | Experience |
| Lower Cellar | Challenges |
| Entry Hall | Disabled (no category) |

### Board View

- All game views render as overlays on background images in `public/`
- Navigation uses a 3x3 invisible hotspot grid over the mansion background
- Hotspot coordinates are percentage-based, independent of artwork
- Clicking a hotspot opens the corresponding room
- Center area of the mansion is non-interactive (atmospheric only)

### Room View

- 6 cards drawn randomly from the room's category (excluding consumed cards)
- Player selects 1 card per room visit
- Selected card moves to center, blurb is visible
- Player classifies: **Proof** or **Objection**
- The Auditor reacts with a single line
- Card is stored as evidence
- Player returns to the mansion

### Deck Behavior

- Selected cards never reappear
- Shown-but-not-selected cards are disabled until no fresh cards remain
- When all eligible cards have been shown, disabled cards are reactivated and
  the deck is reshuffled

### Classification

- Player classifies: Proof or Objection
- Classification is permanent (no undo)
- The Auditor evaluates each classification via a **single LLM call** that
  produces two outputs:
  1. **Score** (-1.0 to 1.0): `score < 0` → Objection, `score >= 0` → Proof
  2. **Narrative reaction**: a short dramatic observation in The Auditor's voice

### Streak

- Display-only metric shown in the UI overlay
- Player picks Proof/Objection, The Auditor grades independently
- If player's classification matches The Auditor's score direction → streak
  increments
- If mismatch → streak resets to 0
- Streak does not affect gameplay, scoring, or final outcome

### Session State Machine

Session state is tracked as an enum:

```
created → exploring → deciding → resolved
```

- **created** — session initialized, no room entered yet
- **exploring** — player is navigating rooms and classifying evidence
- **deciding** — player has at least 1 classification and can Accuse/Pardon
- **resolved** — final decision made, session complete, no further actions

### Session Flow

1. Player enters mansion (session created → `created`)
2. Player navigates rooms and classifies evidence (`exploring`)
3. Evidence is stored in a drawer grouped by classification
4. At least 1 artifact must be evaluated before final decision is enabled
   (transition to `deciding`)
5. Player chooses **Accuse** or **Pardon** (transition to `resolved`)
6. The Auditor evaluates the final decision against all collected evidence,
   determining whether the player's reasoning holds up
7. Session ends — no further evaluations

### Final Output

1. **Resume** — fixed HTML template populated with Proof-classified artifacts
   (template design deferred to implementation, based on LinkedIn format)
2. **Cover Letter** — memorable narrative written by The Auditor using the
   evidence the player collected, reflecting the Accuse/Pardon decision and
   the strength of the case built
3. **Session Summary** — evaluated artifacts, classifications, scores

## The Auditor — AI Character Rules

- Theatrical, dramatic, Clue-board-game energy
- Guides players but never assists or hints at "correct" classifications
- Each classification triggers **one LLM call** → score + narrative reaction
- Adapts tone based on the emerging hypothesis (phase thresholds deferred to
  v2; v1 uses a single tone throughout)
- Writes the cover letter narrative in its own voice using collected evidence
- Evaluates the final Accuse/Pardon decision as the concluding act
- All Auditor output is written to `accusations.ai_audit_run` before client
  delivery (DB trail for troubleshooting, not surfaced in UI)
- v1: Accusation text selected from a static list at session start
- v2: AI-generated accusation derived dynamically from card corpus

## Non-Negotiables

### Testing

- All backend endpoints must have tests
- All frontend components must have tests
- Integration tests for the full game loop (room enter → classify → session end)
- Performance tests for API response times and frontend rendering
- Test coverage is tracked and enforced

### Accessibility

- Full keyboard navigation across board, room, and results views
- Focus management on view transitions
- `prefers-reduced-motion` support for all animations
- Semantic HTML and ARIA attributes where needed
- Screen reader support for card content and classifications

### Performance

- Lighthouse audits must pass
- Performance test suite for critical paths
- Lazy load room backgrounds
- Minimize JS bundle size
- API responses under 200ms for non-AI endpoints

### Security

- No secrets in source control — all secrets via `.env` / Cloud Run env vars
- Supabase RLS enforced on all tables
- Input validation on all API endpoints (Pydantic models)
- CORS restricted to known origins
- No raw SQL — use parameterized queries or ORM
- OWASP top 10 awareness in all code reviews

### GitHub Actions: Action Pinning

- `actions/*` references may use tagged major versions (e.g., `@v6`)
- All other actions must be pinned to a commit SHA with the version in a
  comment (e.g., `@abc123 # v4.1.0`)

### Code Quality

- SonarQube analysis on all PRs
- No code smell or security hotspot regressions
- Conventional commits
- Lefthook pre-commit hooks enforced
- `@checkmarkdevtools/commitlint-plugin-rai` enforced via commitlint + Lefthook

### CodeQL

- CodeQL analysis runs on all PRs and pushes to `main` (`.github/workflows/codeql.yml`)
- Analyzes both `javascript-typescript` and `python`
- **Any finding at any severity fails the build** — there is no minimum severity threshold
- **Inline suppressions are prohibited** (no `// codeql[...]` comments in source)
- To suppress a finding, add an entry to `.github/codeql/suppressions.yml` with:
  - `rule_id`, optional `path_pattern`, `reason`, `approved_by`, `approved_date`
- **Every suppression requires explicit user approval** before merging
- Approved suppressions must also be listed below under "Approved CodeQL Suppressions"

#### Approved CodeQL Suppressions

None approved yet. The list below must be updated whenever a suppression is
added to `.github/codeql/suppressions.yml`.

| Rule ID | Path Pattern | Reason | Approved By | Date |
|---------|-------------|--------|-------------|------|
| — | — | — | — | — |

## v2 Deferred (not in scope for v1)

- Room cooldown mechanics (revisit throttling)
- Narrative phase thresholds (early/mid/late/final tone triggers)
- Session replay from stored session_id
- AI-generated accusation text from card corpus

Tracked on the Monday board under the "v2 Deferred" group.

## Epic & Task Workflow

When instructed to **begin work on an epic**, follow this procedure end-to-end.
When instructed to **complete a task**, follow the same steps but stop after
that task is done (no PR).

### 1. Discover Work

- Access the Monday board (ID `18401136576`) via MCP to find the target epic
  and its subitems (tasks), ordered by their numeric prefix
- Skip any task whose name starts with `— DEFERRED`
- Skip epics marked `Done`

### 2. Branch

- Create a feature branch: `feat/<epic-slug>` (e.g., `feat/canonical-data-session-model`)
- Branch from `main`

### 3. Execute Tasks in Order

For each task in the epic:

1. **Implement** — write source code (API, frontend, migrations, etc.)
2. **Test** — write or update tests; run the full suite; ensure lint + typecheck
   pass (`ruff check`, `mypy --strict`, `eslint`, `svelte-check`)
3. **Commit** — one atomic conventional commit per task, referencing the Monday
   task ID in the footer (`Refs: Monday task <id>`)
4. **Push** — push after each task
5. **Note in Monday** — post an update on the **epic item** summarizing what
   was done

### 4. Self-Review

After all tasks are complete, run a code review covering:

- Adherence to this AGENTS.md
- Security (RLS, secrets, OWASP)
- Code quality (lint, typecheck)
- Test coverage and correctness

Fix all critical and important findings before proceeding.

### 5. Open PR

- Create a PR against `main`
- Post the PR link as a Monday update on the epic item

### 6. Quality Gates (every commit)

- `ruff check` clean, `mypy --strict` clean (API)
- `eslint` clean, `svelte-check` clean (web, when applicable)
- All tests pass, coverage ≥ 85%
- Conventional commits with `Co-Authored-By` trailer
- No secrets in source control
- Anon role is read-only; all DB writes use `service_role`

## What NOT to Do

- Do not modify the `public.cards` schema in Supabase
- Do not store secrets in source control or Docker images
- Do not add authentication — this is a public portfolio experience
- Do not create a "neutral" classification option — only Proof or Objection
- Do not allow classification undo
- Do not show `fact` text to the player before the final reveal
- Do not let The Auditor help players decide — it observes and reacts only
- Do not implement replay, room cooldowns, or phase thresholds (v2)
