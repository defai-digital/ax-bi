# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

This is the **AX-Office fork** of Apache Superset — a data visualization platform with a Flask/Python backend and React/TypeScript frontend. Beyond stock Superset, this fork carries:

- **MCP service** (`superset/mcp_service/`) — a Model Context Protocol server exposing Superset resources to LLM agents. Has its own [`ARCHITECTURE.md`](superset/mcp_service/ARCHITECTURE.md), [`SECURITY.md`](superset/mcp_service/SECURITY.md), and [`PRODUCTION.md`](superset/mcp_service/PRODUCTION.md). **Read those before touching `superset/mcp_service/`.**
- **GenAI BI direction** — see [`GENAI_BI_ROADMAP.md`](GENAI_BI_ROADMAP.md) for the product direction (prompt-to-dashboard, governed semantic layer, AI-ready metadata).
- **Boundary-cleanup effort** — [`BOUNDARY_REPORT.md`](BOUNDARY_REPORT.md) tracks module-boundary findings and which are done vs. deferred. Consult it before large refactors.
- **Upstream Superset sync** — use the controlled merge process in [`docs/developer_docs/upstream-sync-policy.md`](docs/developer_docs/upstream-sync-policy.md). Do not merge upstream PRs blindly; compare against release branches/tags and produce a gap report.
- **`superset-core`** (`superset-core/`) — local editable Python package (`apache-superset-core`) providing shared base classes: `BaseDAO`, `BaseCommand` mixins, `RestApi`, semantic layer types, task framework, and MCP decorators (`superset_core.*` namespace). Changes here propagate to the main app.
- **`ax-services`** (`ax-services/`) — TypeScript sidecar (port 5010) for runtime modernization: health/readiness checks, MCP asset search proxy, and Superset connectivity. Has its own `jest.config.js` and contract schemas in `contracts/`.
- **`superset-desktop`** (`superset-desktop/`) — thin Tauri v2 desktop shell that loads the web app. Rust backend in `src-tauri/`, TypeScript bridge in `src/`. Supports `axbi://` deep links, system tray, and cross-platform builds.
- **`superset-extensions-cli`** (`superset-extensions-cli/`) — CLI tool (`superset-extensions init/build/bundle`) for scaffolding and packaging Superset extensions.
- **`@defai/ax-sdk`** (`packages/ax-sdk/`) — TypeScript SDK providing typed REST + MCP access to AX-Office for downstream products (ax-studio, ax-code). Dual-protocol: REST CRUD for dashboards/charts/datasets/databases/queries, plus AI tool wrappers via MCP (prompt-to-dashboard, semantic search, SQL execution). See [`packages/ax-sdk/README.md`](packages/ax-sdk/README.md).
The agent-instruction files (`CLAUDE.md`, `GEMINI.md`, `GPT.md`) are **symlinks to `AGENTS.md`**. Edit this file — all four update together.

## Naming Policy

AX-Office uses an external rename strategy. Public commands and local development
paths use AX-Office names: `ax-office`, `ax-office-mcp`, and `ax-office-frontend/`.

Keep core Superset namespaces unless a task is explicitly scoped as a full
compatibility migration. This includes `superset/`, `superset_config.py`,
`superset-core/`, `superset-extensions-cli/`, `superset-embedded-sdk/`,
`superset-websocket/`, `helm/superset`, `@superset-ui/*`,
`@apache-superset/core`, and `apache-superset-*` package metadata. These names
preserve upstream sync, imports, migrations, extension contracts, operator
configs, and existing deployments. See
[`docs/developer_docs/ax-office-rename-policy.md`](docs/developer_docs/ax-office-rename-policy.md)
before renaming any remaining `superset*` surface.

## Development Commands

### Backend (Python)

```bash
# Run the development server (port 8088)
ax-office run -p 8088 --with-threads --reload --debugger

# Run the MCP service (port 5008, requires: pip install fastmcp)
ax-office mcp run --port 5008

# Run ALL backend tests
pytest

# Run a single test file
pytest tests/unit_tests/path/to/test_file.py

# Run a single test class or method
pytest tests/unit_tests/path/to/test_file.py::TestClassName::test_method_name

# Run tests in a directory
pytest tests/unit_tests/some_module/

# Database migrations
ax-office db upgrade              # Apply pending migrations
ax-office db migrate -m "description"  # Create a new migration

# Load examples
ax-office load-examples
```

### Frontend (TypeScript/React)

All frontend commands run from `ax-office-frontend/`:

```bash
cd ax-office-frontend

# Development server with hot reload (port 9000)
npm run dev-server

# Production build
npm run build

# Run all tests
npm run test

# Run a single test file
npm run test -- path/to/file.test.tsx

# TypeScript type checking
npm run type

# Lint and auto-fix
npm run lint-fix

# Storybook (component development, port 6006)
npm run storybook
```

### Pre-commit & Quality

```bash
# Install hooks (do this once)
pre-commit install

# IMPORTANT: Stage files first — pre-commit only checks staged files
git add .

# Run on staged files (fast)
pre-commit run

# Run on all files (CI mode, slow)
pre-commit run --all-files

# Individual hooks
pre-commit run mypy                    # Python type checking
pre-commit run prettier-frontend       # Frontend formatting
pre-commit run oxlint-frontend         # Frontend linting
pre-commit run type-checking-frontend  # Frontend tsc

# If auto-fixes applied, re-stage and re-run
git add . && pre-commit run
```

**CI will fail if pre-commit doesn't pass. Always run before pushing.**

Common pre-commit failures:
- **Formatting** — black, prettier will auto-fix
- **Type errors** — mypy (Python) and `type-checking-frontend` (tsc) need manual fixes
- **Linting** — ruff, pylint (Python) and oxlint (frontend) issues; oxlint can auto-fix many with `npm run lint-fix`

### AX Services (TypeScript Sidecar)

All commands run from `ax-services/`:

```bash
cd ax-services
npm install
npm run dev-server     # Development server (port 5010)
npm run build          # Production build
npm test               # Jest tests
npm run type           # TypeScript type checking
npm run contracts:write  # Regenerate contract JSON schemas
```

### AX SDK (`@defai/ax-sdk`)

All commands run from `packages/ax-sdk/`:

```bash
cd packages/ax-sdk
npm install
npm run build       # ESM + CJS + type declarations
npm run test        # Unit tests (Jest, 32 tests)
npm run type        # TypeScript type checking
npm run clean       # Remove dist/
```

The SDK has zero runtime dependencies (uses native `fetch`). It builds dual ESM/CJS outputs with full TypeScript declarations. When changing resource types or adding new AI tool wrappers, update the barrel exports in `src/index.ts`.

### Desktop (Tauri)

```bash
cd superset-desktop
npm install            # First time only
npm run dev            # Builds Rust + launches native window (needs frontend dev-server on :9000)
npm run build          # Release build with platform installers
```

### Playwright E2E Tests

```bash
cd ax-office-frontend
npm run playwright:test                              # All tests
npm run playwright:ui                                # Interactive UI mode
npx playwright test tests/auth/login.spec.ts         # Single file
```

## Architecture

### Backend Layered Pattern

Requests flow through a strict layered architecture. Do not skip layers.

```
HTTP Request
  → Views/API (route handlers, decorators, OpenAPI docstrings)
    → Commands (business logic, validation, @transaction)
      → DAOs (database queries, filtering, pagination)
        → Models (SQLAlchemy ORM, relationships)
```

**Each resource (chart, dashboard, dataset, etc.) follows this structure:**

| Layer | Location | Responsibility |
|-------|----------|---------------|
| API | `superset/views/api.py` or resource-specific `api.py` | Route registration, request parsing, OpenAPI docs, `@protect()` decorator |
| Schemas | `superset/{resource}/schemas.py` | Marshmallow validation schemas for OpenAPI spec |
| Commands | `superset/commands/{resource}/` | Business logic: `Create`, `Update`, `Delete` classes extending `BaseCommand` |
| DAOs | `superset/daos/{resource}.py` | Data access: filtering, pagination, ownership scoping, extending `BaseDAO` |
| Models | `superset/models/` or `superset/connectors/sqla/models.py` | SQLAlchemy ORM definitions |

**Key patterns:**
- Commands extend `BaseCommand` with `run()` and `validate()` methods
- `CreateMixin` / `UpdateMixin` handle owner population
- DAOs extend `BaseDAO` (from `superset_core.common.daos`) with generic CRUD + filtering
- Route authorization uses `@protect()` (REST API), `@has_access_api` (legacy views), or `@has_access` (HTML views)
- Object authorization uses `security_manager.raise_for_access(...)` for data-bearing resources

### `superset-core` Package

The `superset-core/` directory is a standalone Python package (`apache-superset-core`) installed as editable local via `uv`. It provides foundational abstractions used by the main app:

- `superset_core.common.daos` — `BaseDAO` with generic CRUD, filtering, pagination
- `superset_core.common.models` — Shared model mixins
- `superset_core.rest_api` — `RestApi` base class and `@api` decorator
- `superset_core.semantic_layers` — Semantic layer types, DAOs, decorators
- `superset_core.tasks` — Background task framework with `@task` decorator
- `superset_core.mcp` — MCP tool/prompt decorators (`@tool`, `@prompt`)
- `superset_core.queries` — Query types and DAOs

When adding new base abstractions that should be reusable by extensions, put them here rather than in `superset/`.

### Global Extensions (`superset/extensions/__init__.py`)

Singletons initialized once at app startup, imported throughout the codebase:

- `db` — SQLAlchemy instance (database session)
- `appbuilder` — Flask-AppBuilder (RBAC, security)
- `security_manager` — `SupersetSecurityManager` (proxy to `appbuilder.sm`)
- `event_logger` — Structured event logging
- `feature_flag_manager` — Feature flag evaluation
- `cache_manager` — Cache backend management
- `celery_app` — Async task queue

### App Factory (`superset/app.py`)

`create_app()` builds the Flask application using the factory pattern. Configuration loads from `superset.config` module (or `SUPERSET_CONFIG` env var). The `SupersetAppInitializer` in `superset/initialization.py` handles all extension wiring.

### MCP Service Architecture

The MCP service runs as a **separate process** from the Superset web server with its own Flask app singleton (`superset/mcp_service/flask_singleton.py`). Key points:

- Run via CLI: `ax-office mcp run` (see `superset/cli/mcp.py`)
- Each resource (chart, dashboard, dataset, etc.) has a subdirectory with `tool/`, `schemas.py`, and optional `validation/`
- Tool functions decorated with `@mcp.tool` and `@mcp_auth_hook` (manages `g.user`, session lifecycle)
- Shared utilities in `superset/mcp_service/utils/` — use `config_utils.py` for Flask config access, `logging_utils.py` for event logging, `permissions_utils.py` for RBAC checks, `response_utils.py` for serialization
- Common base classes in `superset/mcp_service/common/` — `MCPResourceError` base for error schemas, `mcp_core.py` for `ModelListCore`/`ModelGetInfoCore`/`InstanceInfoCore`
- The MCP service shares the same database and configuration as the web server but has its own HTTP server via FastMCP/Starlette

### Frontend Structure

```
ax-office-frontend/
├── src/
│   ├── features/           # Feature modules (charts, dashboards, datasets, etc.)
│   ├── components/         # Shared reusable components
│   ├── explore/            # Chart builder interface
│   ├── dashboard/          # Dashboard viewer/editor
│   ├── SqlLab/             # SQL editor
│   ├── hooks/              # Custom React hooks
│   ├── utils/              # Shared utilities
│   └── types/              # Shared TypeScript types
├── packages/
│   ├── superset-ui-core/        # Core UI library (USE THIS over raw antd)
│   ├── superset-ui-chart-controls/ # Chart configuration controls
│   └── superset-core/           # Core shared logic
└── plugins/                # Chart plugins (echarts, deck.gl, table, etc.)
```

npm workspaces link `packages/*` and `plugins/*` as local dependencies.

## Ongoing Refactors — What NOT to Do

These migrations are actively happening. Avoid deprecated patterns:

**Frontend:** No `any` types. No `.js`/`.jsx` files (use `.ts`/`.tsx`). Use `@superset-ui/core` components, not raw Ant Design. Use antd theming tokens over legacy tokens. Avoid custom CSS.

**Testing:** Prefer unit > integration > E2E. Use Playwright (not Cypress — deprecated). Use Jest + React Testing Library (Enzyme removed). Use `test()` instead of `describe()` — follow [avoid nesting when testing](https://kentcdodds.com/blog/avoid-nesting-when-youre-testing).

**Backend:** Type hints required on all new Python code. MyPy compliant (`pre-commit run mypy`). SQLAlchemy 1.4 (not 2.0 yet).

**UUIDs:** New models use UUID primary keys. Public APIs expose UUIDs, not internal integer IDs. Existing models add UUID fields alongside integer IDs for gradual migration.

**SQLAlchemy:** Use `~Model.field` instead of `== False` to avoid ruff E712.

## Security Model

Before evaluating any security finding, read [`SECURITY.md`](SECURITY.md). The test: *Does it let a principal perform an action the role/capability matrix does not entitle them to?*

Three trust boundaries:
1. **Admin role** — fully trusted; anything an Admin can do through documented config/API/UI is intended capability
2. **Operator** — owns deployment-time decisions (secrets, network, feature flags, plugins); misconfiguration is a deployment defect
3. **Codebase** — enforces the role/capability matrix at API routes, commands, DAOs, UI handlers

**Route-level authorization** uses one of three Flask-AppBuilder decorators:
- `@protect()` for REST API routes (`ModelRestApi` / `BaseApi`)
- `@has_access_api` for legacy view routes
- `@has_access` for legacy HTML view routes

**Object-level authorization** via `security_manager.raise_for_access(...)` applies to data-bearing resources: dashboards, charts, datasets/datasources, queries, database/table access, and query contexts. Other resources (annotations, tags, CSS templates, reports, RLS rules) rely on route-level decorator plus DAO `base_filters` for ownership scoping — the absence of `raise_for_access` on these is by design.

Automated scanner findings must name the specific SECURITY.md matrix row violated and the assumed attacker principal (Public, Gamma, sql_lab, Alpha, Admin, Embedded guest token, or custom role).

## Code Standards

- **New Python files** require ASF license headers. LLM instruction files (AGENTS.md, etc.) are excluded via `.rat-excludes`.
- **Code comments**: avoid time-specific language ("now", "currently", "today"). Write timeless comments.
- **JSON imports**: use `superset.utils.json` (or `superset.utils.json_fast` for non-ORM performance-critical paths) instead of `json` or `simplejson` (enforced by ruff `banned-api`).
- **Breaking changes**: add to `UPDATING.md`.
- **Docstrings**: required for new functions/classes.
- **Docs**: update `docs/` for user-facing changes.
- **Feature flags**: adding or removing flags in `superset/config.py` triggers the `feature-flags-sync` pre-commit hook, which updates `docs/static/feature-flags.json`. If this hook fails, run it again — the second pass succeeds after the file is updated.

## Test Utilities

**Python:** `SupersetTestCase` base class (`tests/integration_tests/base_tests.py`), `@with_config` / `@with_feature_flags` decorators, `login_as()` / `login_as_admin()` helpers, `create_dashboard()` / `create_slice()` utilities. Use `MagicMock()` for config objects; avoid `AsyncMock` for synchronous code. Test discovery uses `tests/` as root (`pytest.ini`). `asyncio_mode = auto` is set — async test functions run without explicit markers. SQLAlchemy 1.4→2.0 deprecation warnings are configured as errors in `pytest.ini` to prevent regression.

**TypeScript:** Custom `render()` with providers at `ax-bi-frontend/spec/helpers/testing-library.tsx`, `createWrapper()` for Redux/Router/Theme, `selectOption()` helper. React Testing Library only — Enzyme is fully removed.

## Pull Requests

- Read the current template at `.github/PULL_REQUEST_TEMPLATE.md`
- Use [Conventional Commits](https://www.conventionalcommits.org/) for PR titles: `type(scope): description`
- Types: `fix`, `feat`, `docs`, `style`, `refactor`, `perf`, `test`, `chore`

## Migrations

- Location: `superset/migrations/versions/`
- Naming: `YYYY-MM-DD_HH-MM_hash_description.py`
- Use helpers from `superset.migrations.shared.utils` for database compatibility
- MyPy errors are ignored for migration files (see `pyproject.toml` overrides)

## Environment

- Python 3.10+ (see `pyproject.toml` classifiers)
- Node.js (see `ax-office-frontend/package.json` `engines` field — currently ^24.16.0)
- SQLAlchemy 1.4 (not 2.0)
- Backend config: `superset/config.py` (large file — search for specific settings rather than reading entirely)
- Health check: `curl -f http://localhost:8088/health`
- Quick local trial: `docker compose -f docker-compose-non-dev.yml up`
- Full bootstrap: `make install` (installs deps, creates admin, runs migrations, loads examples)
