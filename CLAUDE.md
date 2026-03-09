# CLAUDE.md

Use @AGENTS.md

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

For **each task** in the epic:

1. **Implement** — write source code (API, frontend, migrations, etc.)
2. **Test** — write or update tests; run the full suite; ensure lint + typecheck pass
3. **Document** — add or update architecture docs in `docs/architecture/` with
   mermaid diagrams (ER, state machines, sequence, flow) at each viable stage
4. **Commit** — one atomic conventional commit per task, referencing the Monday
   task ID in the footer (`Refs: Monday task <id>`)
5. **Push** — push after each task
6. **Note in Monday** — post an update on the **epic item** (not the subitem,
   since subitem column updates are unauthorized) summarizing what was done

### 4. Self-Review

After all tasks are complete, run a code review agent covering:

- Adherence to AGENTS.md specs
- Security (RLS, secrets, OWASP)
- Code quality (ruff, mypy, eslint, typecheck)
- Test coverage and correctness

Fix all critical and important findings before proceeding.

### 5. Open PR

- Create a PR against `main` with:
  - Summary bullets
  - Architecture diagram references
  - Test plan checklist
- Post the PR link as a Monday update on the epic item

### 6. Non-Negotiables (every commit)

- `ruff check` clean, `mypy --strict` clean (API)
- `eslint` clean, `svelte-check` clean (web, when applicable)
- All tests pass, coverage ≥ 85%
- Conventional commits with `Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>`
- No secrets in source control
- Anon role is read-only; all DB writes use `service_role`
