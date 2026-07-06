# AGENTS.md

This file provides guidance to Qoder (qoder.com) when working with code in this repository.

## Project Overview

This is the **AX-BI fork** of Apache Superset — a data visualization platform with a Flask/Python backend and React/TypeScript frontend. Beyond stock Superset, this fork carries:

- **MCP service** (`superset/mcp_service/`) — a Model Context Protocol server exposing Superset resources to LLM agents. Has its own [`ARCHITECTURE.md`](superset/mcp_service/ARCHITECTURE.md), [`SECURITY.md`](superset/mcp_service/SECURITY.md), and [`PRODUCTION.md`](superset/mcp_service/PRODUCTION.md). **Read those before touching `superset/mcp_service/`.**
- **GenAI BI direction** — see [`GENAI_BI_ROADMAP.md`](GENAI_BI_ROADMAP.md) for the product direction (prompt-to-dashboard, governed semantic layer, AI-ready metadata).
- **Boundary-cleanup effort** — [`BOUNDARY_REPORT.md`](BOUNDARY_REPORT.md) tracks module-boundary findings and which are done vs. deferred. Bug write-ups live in `ax-internal/bugs/`. Consult these before large refactors.
- **`superset-core`** (`superset-core/`) — local editable Python package (`apache-superset-core`) providing shared base classes: `BaseDAO`, `BaseCommand` mixins, `RestApi`, semantic layer types, task framework, and MCP decorators (`superset_core.*` namespace). Changes here propagate to the main app.
- **`ax-services`** (`ax-services/`) — TypeScript sidecar (port 5010) for runtime modernization: health/readiness checks, MCP asset search proxy, and Superset connectivity. Has its own `jest.config.js` and contract schemas in `contracts/`.
- **`superset-desktop`** (`superset-desktop/`) — thin Tauri v2 desktop shell that loads the web app. Rust backend in `src-tauri/`, TypeScript bridge in `src/`. Supports `axbi://` deep links, system tray, and cross-platform builds.
- **`superset-extensions-cli`** (`superset-extensions-cli/`) — CLI tool (`superset-extensions init/build/bundle`) for scaffolding and packaging Superset extensions.
- **`ax-internal/`** — internal design docs (`docs/`), reference implementations (`reference/evidence/`), and bug reports (`bugs/`). Read before starting features covered by existing ADRs/PRDs.

The agent-instruction files (`CLAUDE.md`, `GEMINI.md`, `GPT.md`) are **symlinks to `AGENTS.md`**. Edit this file — all four update together.

## Development Commands

### Backend (Python)

```bash
# Run the development server (port 8088)
superset run -p 8088 --with-threads --reload --debugger

# Run the MCP service (port 5008, requires: pip install fastmcp)
superset mcp run --port 5008

# Run ALL backend tests
pytest

# Run a single test file
pytest tests/unit_tests/path/to/test_file.py

# Run a single test class or method
pytest tests/unit_tests/path/to/test_file.py::TestClassName::test_method_name

# Run tests in a directory
pytest tests/unit_tests/some_module/

# Database migrations
superset db upgrade              # Apply pending migrations
superset db migrate -m "description"  # Create a new migration

# Load examples
superset load-examples
```

### Frontend (TypeScript/React)

All frontend commands run from `superset-frontend/`:

```bash
cd superset-frontend

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

### Desktop (Tauri)

```bash
cd superset-desktop
npm install            # First time only
npm run dev            # Builds Rust + launches native window (needs frontend dev-server on :9000)
npm run build          # Release build with platform installers
```

### Playwright E2E Tests

```bash
cd superset-frontend
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

- Run via CLI: `superset mcp run` (see `superset/cli/mcp.py`)
- Each resource (chart, dashboard, dataset, etc.) has a subdirectory with `tool/`, `schemas.py`, and optional `validation/`
- Tool functions decorated with `@mcp.tool` and `@mcp_auth_hook` (manages `g.user`, session lifecycle)
- Shared utilities in `superset/mcp_service/utils/` — use `config_utils.py` for Flask config access, `logging_utils.py` for event logging, `permissions_utils.py` for RBAC checks, `response_utils.py` for serialization
- Common base classes in `superset/mcp_service/common/` — `MCPResourceError` base for error schemas, `mcp_core.py` for `ModelListCore`/`ModelGetInfoCore`/`InstanceInfoCore`
- The MCP service shares the same database and configuration as the web server but has its own HTTP server via FastMCP/Starlette

### Frontend Structure

```
superset-frontend/
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

### TypeScript Project References

The frontend uses [TypeScript Project References](https://www.typescriptlang.org/docs/handbook/project-references.html) to structure the codebase as a set of smaller, interconnected projects rather than one monolithic compilation unit. This setup is critical for incremental builds, faster type-checking, and clear module boundaries.

**How it works:**

- The root `ax-office-frontend/tsconfig.json` declares `"composite": true` and lists every sub-project in the `"references"` array (packages and plugins).
- Each sub-project (`packages/superset-ui-core/`, `packages/superset-ui-chart-controls/`, `packages/superset-core/`, and every plugin under `plugins/`) has its own `tsconfig.json` with `"composite": true`. This produces `.d.ts` declaration files that downstream projects consume.
- Path aliases in the root `tsconfig.json` (`"paths"` field) map `@superset-ui/core`, `@superset-ui/chart-controls`, `@apache-superset/core`, etc. to their respective `src/` directories so that IDEs and bundlers resolve to live source rather than stale build output.

**Common pitfalls:**

- **Stale `lib/` directories**: Each sub-project's `declarationDir` is `lib/`. If `lib/` is not excluded from the root `include` patterns, TypeScript will try to compile the generated `.d.ts` files as part of the program, causing hundreds of "file not found" errors. The root `tsconfig.json` must include `"**/lib/**"` in its `"exclude"` array.
- **Forgetting to rebuild**: After changing a shared package (e.g., `superset-ui-core`), dependent plugins need the updated declarations. Run `npm run type` from the root to trigger an incremental build across all referenced projects in dependency order.
- **Adding a new plugin/package**: You must (1) create a `tsconfig.json` with `"composite": true` in the new directory, and (2) add a `{ "path": "./plugins/<name>" }` entry to the root `tsconfig.json` `references` array. Without this, cross-project type resolution will silently fall back to `node_modules` and may use stale declarations.

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

**TypeScript:** Custom `render()` with providers at `superset-frontend/spec/helpers/testing-library.tsx`, `createWrapper()` for Redux/Router/Theme, `selectOption()` helper. React Testing Library only — Enzyme is fully removed.

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
- Node.js (see `superset-frontend/package.json` `engines` field — currently ^24.16.0)
- SQLAlchemy 1.4 (not 2.0)
- Backend config: `superset/config.py` (large file — search for specific settings rather than reading entirely)
- Health check: `curl -f http://localhost:8088/health`
- Quick local trial: `docker compose -f docker-compose-non-dev.yml up`
- Full bootstrap: `make install` (installs deps, creates admin, runs migrations, loads examples)
