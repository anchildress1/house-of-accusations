# House of Accusations

<!-- Banner image: add one at public/banner.png and uncomment below -->
<!-- ![Banner](./public/banner.png) -->

[![CI](https://github.com/anchildress1/house-of-accusations/actions/workflows/ci.yml/badge.svg)](https://github.com/anchildress1/house-of-accusations/actions/workflows/ci.yml)
[![License: Polyform Shield](https://img.shields.io/badge/license-Polyform%20Shield-blue)](LICENSE)
[![Quality Gate](https://sonarcloud.io/api/project_badges/measure?project=anchildress1_house-of-accusations&metric=alert_status)](https://sonarcloud.io/project/overview?id=anchildress1_house-of-accusations)
[![Coverage](https://sonarcloud.io/api/project_badges/measure?project=anchildress1_house-of-accusations&metric=coverage)](https://sonarcloud.io/project/overview?id=anchildress1_house-of-accusations)

An interactive developer portfolio disguised as a mansion investigation game. Players explore rooms, evaluate evidence cards, and build a case — producing a generated resume and cover letter at the end of the session.

## Setup

```bash
# Install dependencies
make install

# Start development servers
make dev
```

## Available Commands

| Command | Description |
|---|---|
| `make install` | Install all dependencies (web + api) |
| `make dev` | Start both development servers |
| `make format` | Format code (web + api) |
| `make lint` | Run linters (web + api) |
| `make typecheck` | Type check (web + api) |
| `make test` | Run unit tests (web + api) |
| `make build` | Production build |
| `make e2e` | Run Playwright E2E tests |
| `make perf` | Run Lighthouse performance tests |
| `make secret-scan` | Scan for secrets |
| `make clean` | Remove build artifacts |

## Architecture

| Layer | Technology |
|---|---|
| Frontend | SvelteKit (`web/`) |
| Backend | FastAPI (`api/`) |
| AI SDK | Anthropic Python SDK |
| Database | Supabase (PostgreSQL) |
| Deploy | Cloud Run (2 services) |

## License

Polyform Shield License 1.0.0 — see [LICENSE](LICENSE).
