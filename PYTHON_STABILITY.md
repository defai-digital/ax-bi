# AX BI Python Stability Plan

This document records the stability assessment of AX BI's Python backend
(Superset-era lineage) and the phased hardening plan. It complements
[`BOUNDARY_REPORT.md`](BOUNDARY_REPORT.md) (module boundaries) and
[`SECURITY.md`](SECURITY.md) (authorization).

## Assessment summary

Review consensus that "Superset Python is not stable enough" maps to a few
repeatable classes of defect—not random flakiness. In this fork the highest
risk areas are:

| Risk class | Evidence in this tree | Impact |
| --- | --- | --- |
| Session lifecycle leaks | Scoped session reuse after failed connections (MCP auth bug, fixed); Celery `task_postrun` previously used bare `remove()` and skipped cleanup when eager | Cross-request contamination, stuck workers |
| Transaction boundaries | `@transaction` was boolean-nested; raw `db.session.commit()` still common in SQL execution paths | Partial writes, swallowed failures |
| Broad exception handling | ~240 `broad-except` / `BLE001` suppressions; some silent `pass` | Hard-to-diagnose production failures |
| Legacy SQLAlchemy style | ~340 `session.query(...)` call sites; SA2 banned APIs already guarded | Future SA major breakage |
| God modules | `security/manager.py` (~4.5k LOC), `models/helpers.py` (~3.9k), `viz.py` (~3k), `config.py` (~3.2k) | High regression cost on touch |
| Environment drift | Project requires Python **≥3.12**; a local `venv` on 3.11 cannot install `ax-bi-core` | Broken local tests / false confidence |

What is already in good shape:

- Layered API → Command → DAO → Model pattern with `@transaction` and
  `BaseDAO`.
- SQLAlchemy 2 removed-API contract tests
  (`tests/unit_tests/test_sqlalchemy2_compatibility.py`).
- MCP session recovery and many boundary cleanups (see `BOUNDARY_REPORT.md`).
- Large unit-test suite under `tests/unit_tests/`.

## Stability principles (best practices we enforce)

1. **One unit of work, one outer commit** — use `@transaction` at command
   boundaries; nested calls must not commit early.
2. **Fail closed on auth; fail soft on cleanup** — never let rollback/remove
   mask a primary exception, but always attempt recovery.
3. **No bare `except:`** — catch specific types or log `Exception` with
   `exc_info`.
4. **DAOs own queries; commands own transactions** — keep session mutation out
   of transport layers (views, MCP tools) on happy paths.
5. **Static guards for known-bad patterns** — mechanical tests that fail CI when
   banned APIs reappear.
6. **Python 3.12+ only** — match `pyproject.toml` / `Makefile` (`python3.12`).

## Phase plan

### Phase 0 — Foundations (this change set)

- Shared `axbi/utils/session_lifecycle.py` for rollback/remove with DBAPI
  recovery; MCP re-exports the same boundary.
- Harden `@transaction` with a depth counter and safe rollback.
- Celery `task_postrun` always removes the scoped session safely when an app
  context exists.
- Soft-fail + log when persisting SQL Lab FAILED status cannot commit.
- Log (do not silently ignore) frontend asset-manifest parse failures.
- Document `BaseCommand.execute()` for transport call sites.
- Static guards in `tests/unit_tests/test_python_stability_guards.py`.

### Phase 1 — Transaction convergence (this batch)

- Added `commit_session(session, *, context, soft=...)` and session-scoped
  `rollback_session` so a failed metadata write always rolls back before
  returning control.
- Converted `axbi/sql/execution/celery_task.py`,
  `axbi/sql/execution/executor.py`, and report `create_log` in
  `axbi/commands/report/execute.py` to those helpers (user-DB `conn.commit()`
  for SQL mutations intentionally unchanged).
- Unit tests cover soft/hard commit failure recovery and structural guards
  ban raw `db.session.commit()` on those hot paths.

### Phase 1.1 — Security and state-machine hardening

- SQL Lab cost estimation authorizes the referenced SQL with strict dataset
  matching; formatting authorizes template-backed database access before Jinja
  macros can execute.
- Virtual-dataset RLS application and RLS cache-key collection fail closed.
- Legacy SQL Lab error persistence uses session-lifecycle helpers, and long
  query execution changes `expire_on_commit` on the concrete session.
- GTF terminal transitions merge task properties under a row lock, flush
  throttled progress first, synchronize ORM state after compare-and-swap, and
  serialize abort/timeout detection across threads.
- Distributed locks carry per-acquisition owner tokens and release with
  compare-and-delete semantics.
- Sidecar deployments require inbound bearer authentication on non-loopback
  listeners; Docker Compose keeps the sidecar private to the service network.

### Phase 2 — SQLAlchemy 2 style migration (incremental)

- Replace `session.query(Model)` with `select(Model)` / `session.scalars` in
  DAOs first (highest reuse), file-by-file with tests.
- Keep the existing banned-API scanner; optionally track `session.query` count
  as a ratchet (do not fail CI on legacy count yet).

### Phase 3 — God-module reduction (design-driven)

- Split `AxBISecurityManager` by concern (dataset access, guest tokens, RBAC
  sync) only with focused tests and SECURITY.md matrix coverage.
- Extract viz payload builders from `viz.py` behind the query-context path
  already used by modern charts.

### Phase 4 — Exception hygiene

- Convert silent broad-except/pass in request paths to structured logging +
  domain errors.
- Prefer typed command exceptions over bare `Exception` at API boundaries.

## Local environment checklist

```bash
# Prefer the Makefile target so the venv is Python 3.12
make venv
source venv/bin/activate
uv pip install -r requirements/development.txt
uv pip install -e ax-bi-core
uv pip install -e .

# Focused stability suite
pytest tests/unit_tests/test_python_stability_guards.py \
       tests/unit_tests/test_sqlalchemy2_compatibility.py \
       tests/unit_tests/utils/test_session_lifecycle.py \
       tests/unit_tests/utils/test_decorators.py \
       tests/unit_tests/mcp_service/utils/test_session_utils.py -q
```

## Definition of done (ongoing)

A stability improvement is "done" only when:

1. It has a focused unit test (or expands a static guard).
2. It does not widen authorization surface (see SECURITY.md).
3. Session cleanup cannot skip `remove()` after a failed `rollback()`.
4. Nested unit-of-work call sites still commit once at the outermost boundary.
