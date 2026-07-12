# AX BI Boundary Report

This report tracks active module-boundary decisions for the AX BI fork. It is
intended as a concise guide for future refactors, not a changelog of completed
mechanical cleanup.

## Current Status

The low-risk boundary cleanup pass is complete. Completed work included:

- Centralizing repeated MCP response serialization, select-column parsing,
  request defaulting, pagination conversion, structured filter parsing, and
  error-schema factories.
- Centralizing MCP list/get-info response finalization and event logging through
  narrow utility boundaries.
- Moving repeated MCP configuration reads into `config_utils.py`.
- Moving selected MCP permission checks into `permissions_utils.py`.
- Centralizing naive-UTC database timestamp helpers and prune batch deletion
  mechanics.
- Replacing repeated frontend CRUD list page-size constants with a shared
  constant.
- Aligning CI database identities and translation baselines with the canonical
  runtime/package boundaries, backed by repository-level contract tests.
- Replacing the legacy Python license scanner's removed `pkg_resources`
  dependency and excluding generated AX Office compatibility artifacts from
  source control.
- Moving report execution state and log construction behind report DAOs, and
  consolidating duration logging on a monotonic command helper while retaining
  command-owned transaction and exception boundaries.
- Moving the privacy-scoped MCP user-filter resolver query into `UserDAO`, with
  bounded results, literal wildcard matching, and DAO-level nonblank
  enforcement.
- Routing MCP saved-query creation through a command-owned validation and
  transaction boundary instead of querying and committing inside the tool.
- Moving best-effort GenAI artifact and evaluation audit writes behind
  transaction-owning commands and DAOs so persistence failures roll back before
  the workflow degrades silently.
- Converging MCP dashboard generation and GenAI composition on a shared
  command-owned persistence boundary that re-resolves charts and owners in the
  active session before attaching relationships atomically.
- Routing failed generated-chart cleanup through the transactional delete
  command so compile-check failures cannot leave a chart visible after the tool
  reports that it was discarded.
- Moving chart state refreshes behind `ChartDAO`, keeping ORM session access out
  of MCP tool happy paths while routing failed-request rollback through a shared
  MCP session boundary.
- Routing chart and database entity lookups in mutating/SQL-execution tools
  through their resource DAOs while preserving explicit object authorization
  and not-found behavior.
- Moving dashboard-filter, preview-dataset, post-upload dataset, and semantic
  alias reads behind resource DAOs; semantic aliases are scoped by both object
  name and dataset so unrelated columns cannot inherit each other's aliases.
- Centralizing MCP scoped-session recovery in `session_utils.py`: authentication
  uses strict, connection-aware removal before user resolution, while error
  paths attempt rollback and removal independently without masking the primary
  failure. MCP tool modules no longer mutate scoped sessions directly.

## Deferred Boundary Areas

These areas are intentionally not cleaned up through small opportunistic edits.
They need explicit design, ownership, and wider test coverage before refactor.

| Area | Why deferred | Suggested next step |
| --- | --- | --- |
| MCP tool modules and AxBI globals | Tool transport, auth, configuration, logging, persistence, and Flask context are still coupled in parts of `axbi/mcp_service/`. Broad extraction would affect execution and auth paths. | Pick one boundary at a time, starting with a narrow adapter that has existing tests or can receive focused tests. |
| Frontend list pages | CRUD list pages still repeat orchestration around `useListViewResource`, permissions, filters, bulk actions, and sorting. A shared abstraction could easily become too broad. | Extract only one repeated behavior after tests document it across at least two list pages. |
| Pandas postprocessing compatibility | Version-compatibility branches live near transformation logic. They are small and covered by focused tests. | Leave local unless more pandas-version branches appear. |

## Refactor Guidance

Before starting one of the deferred areas:

- Read the relevant local architecture docs, especially the MCP service docs
  before touching `axbi/mcp_service/`.
- Prefer small shared helpers over new framework-style abstractions.
- Keep resource-specific DAO, security, validation, and serialization behavior
  local unless duplication is proven and tested.
- Add or update focused tests for the boundary being moved.
