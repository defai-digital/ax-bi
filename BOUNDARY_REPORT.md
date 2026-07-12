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
- Moving the privacy-scoped MCP user-filter resolver query into `UserDAO`, with
  bounded results, literal wildcard matching, and DAO-level nonblank
  enforcement.

## Deferred Boundary Areas

These areas are intentionally not cleaned up through small opportunistic edits.
They need explicit design, ownership, and wider test coverage before refactor.

| Area | Why deferred | Suggested next step |
| --- | --- | --- |
| MCP tool modules and AxBI globals | Tool transport, auth, configuration, logging, persistence, and Flask context are still coupled in parts of `axbi/mcp_service/`. Broad extraction would affect execution and auth paths. | Pick one boundary at a time, starting with a narrow adapter that has existing tests or can receive focused tests. |
| Frontend list pages | CRUD list pages still repeat orchestration around `useListViewResource`, permissions, filters, bulk actions, and sorting. A shared abstraction could easily become too broad. | Extract only one repeated behavior after tests document it across at least two list pages. |
| Report command workflow | Timestamp consistency has been fixed, but report execution still mixes state persistence and elapsed-time branches. | Treat as a command workflow refactor, not a cleanup patch. |
| Pandas postprocessing compatibility | Version-compatibility branches live near transformation logic. They are small and covered by focused tests. | Leave local unless more pandas-version branches appear. |

## Refactor Guidance

Before starting one of the deferred areas:

- Read the relevant local architecture docs, especially the MCP service docs
  before touching `axbi/mcp_service/`.
- Prefer small shared helpers over new framework-style abstractions.
- Keep resource-specific DAO, security, validation, and serialization behavior
  local unless duplication is proven and tested.
- Add or update focused tests for the boundary being moved.
