# AX-BI Stabilization Bug Report

_Scope: the uncommitted working-tree changeset on `master` (a pandas 2.x→3.x +
timezone-aware-datetime migration, plus security hardening and a11y work).
Active project only. No vendor/internal, architecture, or migration changes._

## 1. Stability check summary

| Check | Tool | Result |
|-------|------|--------|
| Python lint | `ruff check superset/` | ✅ clean |
| Python unit tests | `pytest tests/unit_tests/` | ✅ 8462 passed, 4 skipped |
| Frontend lint | `oxlint --quiet` (changed files) | ✅ no errors (warnings only) |
| Frontend types | `tsc --noEmit` (whole project) | ✅ clean |
| Dependencies | `pip check` | ✅ no broken requirements |

Build, test, lint, type, and dependency health are all green. Integration
tests (`tests/integration_tests/**`) require a live metadata DB and were not run
in this environment.

## 2. Confirmed bugs — FIXED

All four were naive/aware `datetime` regressions introduced by the timezone
migration (`datetime.utcnow()` → `datetime.now(timezone.utc)`), which silently
changed naive UTC datetimes into tz-aware ones. Each fix is small and restores
the original naive-UTC semantics the surrounding code/DB columns expect.

### BUG-1 (HIGH) — Temporal filters broken across most DB engines
- **File:** `superset/models/helpers.py` (`filter_values_handler`, ~line 2541)
- **Cause:** epoch filter value converted with `fromtimestamp(..., tz=utc)`
  (aware) and passed to `db_engine_spec.convert_dttm`, whose implementations
  format with `isoformat()`/`strftime()`. The aware value appends `+00:00`, so
  e.g. Postgres `TO_TIMESTAMP('...+00:00', 'YYYY-MM-DD HH24:MI:SS.US')` and
  MySQL `STR_TO_DATE` (no TZ token) produce parse errors / `NULL`.
- **Fix:** `.replace(tzinfo=None)` to keep the datetime naive UTC.
- **Validation:** repro confirmed offset difference; `convert_dttm` spec tests
  (7) and full unit suite pass.

### BUG-2 (HIGH) — Recent-activity endpoint crash
- **File:** `superset/daos/log.py` (~line 145)
- **Cause:** `datetime.now(timezone.utc) - log.dttm` subtracts a naive column
  (`Log.dttm`) from an aware value → `TypeError: can't subtract offset-naive
  and offset-aware datetimes`.
- **Fix:** subtract a naive-UTC "now".

### BUG-3 (HIGH) — Report-log pruning broken on PostgreSQL
- **File:** `superset/commands/report/log_prune.py` (~line 44)
- **Cause:** cutoff computed as tz-aware and compared against the naive
  `ReportExecutionLog.end_dttm` column — the exact naive/aware mismatch the
  sibling `logs/prune.py` already guards against (it strips tzinfo; this file
  did not).
- **Fix:** `.replace(tzinfo=None)` on the cutoff.

### BUG-4 (MEDIUM) — Account-disable session enforcement can silently no-op
- **File:** `superset/security/session_invalidation.py`
  (`_get_user_invalidated_at`)
- **Cause:** on the unauthenticated-but-session-present path,
  `session["_user_id"]` is a **string** (Flask-Login), but it is used in
  `filter_by(user_id=...)` against an `Integer` column. On strict backends this
  raises, and the broad `except` swallows it — defeating the disabled-user
  check.
- **Fix:** coerce `user_id` to `int` at the boundary.

### BUG-5 (MEDIUM, pre-existing) — `task_subscribers.subscribed_at` default frozen at import time
- **File:** `superset/models/task_subscribers.py:51`
- **Cause:** `default=datetime.now(timezone.utc)` **calls** the function at class
  definition (import) time, passing a fixed scalar. SQLAlchemy then reuses that
  single timestamp for every inserted row that relies on the default. Every
  other model in the repo passes a callable (`default=datetime.now` /
  `datetime.utcnow`).
- **Impact:** latent — the creation DAO (`daos/tasks.py`) sets `subscribed_at`
  explicitly, so the default is bypassed there; but any other insert path
  (tests, bulk inserts, future code) would record a stale, identical timestamp.
- **Fix:** `default=lambda: datetime.now(timezone.utc)` (callable, evaluated
  per row; matches the DAO's UTC intent).
- **Validation:** ruff clean; 8 task unit tests pass.

## 3. Confirmed issue — FIXED

### ISSUE-1 (MEDIUM, pre-existing) — Key-value / distributed-lock expiry mixes UTC and local time
- **Files:** `superset/commands/distributed_lock/acquire.py`, `superset/key_value/models.py`, `superset/key_value/commands/prune.py`, `superset/daos/key_value.py`.
- **Cause:** `acquire.py` wrote aware-UTC `expires_on`, while `is_expired()`, `prune`, and the DAO compared against `datetime.now()` (naive local). On non-UTC servers, lock/KV entries expired at the wrong time.
- **Fix:** aligned all 8 call sites to use the shared `naive_utcnow()` helper, ensuring consistent naive-UTC writes and comparisons.
- **Validation:** ruff clean; 5 prune tests, 19 DAO key-value tests, and 8 distributed-lock tests pass.

## 4. Reviewed and confirmed correct (not bugs)

- pandas 3.x compat (`boxplot`, `pivot`, `resample`, `rolling`,
  postprocessing `utils`) — guarded, behavior-preserving.
- Importer SSH-tunnel join — fixes a real pre-existing keying bug (was keyed by
  tunnel UUID, now correctly by database UUID).
- `models/slice.py` `slice_link` — URL now escaped (XSS hardening).
- Drill-info authz, CSRF-requires-auth, logout session invalidation — intended
  hardening.
- MCP `schema` → `schema_name` alias — avoids Pydantic `BaseModel.schema()`
  shadowing; covered by new tests.
- `execute_sql` — behavior-preserving extract-method refactor.
- `TaskList/index.tsx` — fixes a React rules-of-hooks violation (early return
  was between hook calls).
- `SavedQueryList` / `DatasetList` — corrected `useMemo`/`useCallback`
  dependency arrays (stale-closure fixes).
- `AsyncIcon` / `Echart` — dynamic template-literal imports converted to static
  loader maps (bundler-compat); coverage verified complete (25/25 icons; all 23
  echarts locale paths resolve).

## 5. Minor observations (not fixed — pre-existing, non-blocking)

- ~~`superset-frontend/src/pages/ChartList/index.tsx:19,29` — duplicate import from `@apache-superset/core/theme`~~ — ✅ Fixed (merged into single import).
- Repo-wide mypy baseline (~1081 errors across 186 files, e.g. `LocalProxy`
  `event_logger` attribute errors) is pre-existing and unrelated to this
  changeset; gated by pre-commit, out of scope for stabilization.

## 6. Not yet verified (needs environment)

- Integration tests (`tests/integration_tests/**`) — require a running metadata
  DB; recommend running before merge.
- `pre-commit run --all-files` — recommended as the final mechanical gate.
</content>
</invoke>
