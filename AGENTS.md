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

### Card Access Rules

- Cards come from `public.cards` where `signal > 2`
- Use existing column names as-is (`title`, `blurb`, `fact`, `category`,
  `objectID`). Do not rename columns.
- The `fact` column is hidden from the player until the final reveal.
- The Auditor sees `fact` immediately upon card draw.

### Audit Storage

Evaluation results are written to `accusations.ai_audit_run` before the
client response is sent. Fields: `session_id`, `chosen_card_id`,
`user_position`, `contract_name`, `contract_version`, `final_score`,
`raw_output_text`.

## Game Rules

### Room Map (3x3 Grid)

```
Hidden Attic    |  Gallery     |  Parlor
Control Room    |  Entry Hall  |  Library
Lower Cellar    |  Workshop    |  Back Hall
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

- Navigation uses a 3x3 invisible hotspot grid over the mansion background
- Hotspot coordinates are percentage-based, independent of artwork
- Clicking a hotspot opens the corresponding room

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
- The Auditor evaluates each classification, scoring -1.0 to 1.0
  - `score < 0` → Objection
  - `score >= 0` → Proof (0 counts as Proof)

### Session Flow

1. Player enters mansion (session created)
2. Player navigates rooms and classifies evidence
3. Evidence is stored in a drawer grouped by classification
4. At least 1 artifact must be evaluated before final decision is enabled
5. Player chooses **Accuse** or **Pardon**
6. The Auditor evaluates the final decision against all collected evidence,
   determining whether the player's reasoning holds up
7. Session ends — no further evaluations

### Final Output

1. **Resume** — static template populated with Proof-classified artifacts
2. **Cover Letter** — memorable narrative written by The Auditor using the
   evidence the player collected, reflecting the Accuse/Pardon decision and
   the strength of the case built
3. **Session Summary** — evaluated artifacts, classifications, scores

## The Auditor — AI Character Rules

- Theatrical, dramatic, Clue-board-game energy
- Guides players but never assists or hints at "correct" classifications
- Reacts to each classification with a short observation
- Adapts tone based on the emerging hypothesis (early/mid/late/final phases)
- Writes the cover letter narrative in its own voice using collected evidence
- Evaluates the final Accuse/Pardon decision as the concluding act
- All Auditor output is audited before client delivery

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

## What NOT to Do

- Do not modify the `public.cards` schema in Supabase
- Do not store secrets in source control or Docker images
- Do not add authentication — this is a public portfolio experience
- Do not create a "neutral" classification option — only Proof or Objection
- Do not allow classification undo
- Do not show `fact` text to the player before the final reveal
- Do not let The Auditor help players decide — it observes and reacts only
