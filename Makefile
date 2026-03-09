.PHONY: install dev format format-check lint typecheck test build e2e perf secret-scan clean \
       install-web install-api dev-web dev-api format-web format-api lint-web lint-api \
       typecheck-web typecheck-api test-web test-api build-web build-api

# ============================================================
# Aggregate targets (run both web + api)
# ============================================================

install: install-web install-api

dev:
	@echo "Starting both servers..."
	$(MAKE) dev-api &
	$(MAKE) dev-web

format: format-web format-api

format-check:
	@cd web && pnpm format:check
	@cd api && uv run ruff format --check .

lint: lint-web lint-api

typecheck: typecheck-web typecheck-api

test: test-web test-api

build: build-web build-api

e2e: build-web
	@echo "Running E2E tests..."
	@cd web && pnpm exec playwright test

perf:
	@echo "Running Lighthouse + performance tests..."
	@cd web && pnpm exec lhci autorun

secret-scan:
	@echo "Scanning for secrets..."
	@_run_scan() { \
		SCANNER="$$1"; \
		$$SCANNER scan --exclude-files 'node_modules|dist|.svelte-kit|.venv|.secrets.baseline|.secrets.baseline.tmp' > .secrets.baseline.tmp 2>&1 || true; \
		if [ ! -f .secrets.baseline.tmp ]; then \
			echo "detect-secrets scan did not produce output. Skipping."; \
			return 0; \
		fi; \
		if [ -f .secrets.baseline ]; then \
			echo "Checking against baseline..."; \
			NEW_SECRETS=$$($$SCANNER scan --baseline .secrets.baseline --exclude-files 'node_modules|dist|.svelte-kit|.venv' | jq '.results | length' 2>/dev/null || echo 0); \
			if [ "$${NEW_SECRETS:-0}" -gt 0 ]; then \
				echo "New secrets found! Run 'detect-secrets audit .secrets.baseline' to review."; \
				$$SCANNER scan --baseline .secrets.baseline --exclude-files 'node_modules|dist|.svelte-kit|.venv' | jq '.results'; \
				rm -f .secrets.baseline.tmp; \
				return 1; \
			else \
				echo "No new secrets found. Updating baseline timestamp."; \
				[ -f .secrets.baseline.tmp ] && mv .secrets.baseline.tmp .secrets.baseline || true; \
			fi; \
		else \
			[ -f .secrets.baseline.tmp ] && mv .secrets.baseline.tmp .secrets.baseline && echo "Secrets baseline created at .secrets.baseline" || echo "Could not create baseline."; \
		fi; \
	}; \
	if command -v uvx > /dev/null; then \
		_run_scan "uvx --from detect-secrets==1.5.0 detect-secrets" || exit 1; \
	elif command -v detect-secrets > /dev/null; then \
		_run_scan "detect-secrets" || exit 1; \
	else \
		echo "detect-secrets not found. Skipping scan."; \
	fi

clean:
	rm -rf web/node_modules web/.svelte-kit web/build web/coverage web/playwright-report
	rm -rf api/.venv api/__pycache__ api/.pytest_cache api/.ruff_cache api/htmlcov
	rm -f .secrets.baseline.tmp

# ============================================================
# Web (SvelteKit)
# ============================================================

install-web:
	@echo "Installing web dependencies..."
	@cd web && pnpm install

dev-web:
	@cd web && pnpm dev

format-web:
	@cd web && pnpm format

lint-web:
	@cd web && pnpm lint

typecheck-web:
	@cd web && pnpm typecheck

test-web:
	@echo "Running web tests..."
	@cd web && pnpm test

build-web:
	@echo "Building web..."
	@cd web && pnpm build

# ============================================================
# API (FastAPI)
# ============================================================

install-api:
	@echo "Installing API dependencies..."
	@cd api && uv sync

dev-api:
	@cd api && uv run uvicorn house_of_accusations.main:app --reload --port 8080

format-api:
	@cd api && uv run ruff format .

lint-api:
	@cd api && uv run ruff check .

typecheck-api:
	@cd api && uv run mypy .

test-api:
	@echo "Running API tests..."
	@cd api && uv run pytest

build-api:
	@echo "API is Python — no build step required."
