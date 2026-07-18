# Recovery: product stability from `ax-bi-desktop-v2.0.5`

**Status:** active  
**Golden baseline:** tag `ax-bi-desktop-v2.0.5` (`0539100a65217c4156327e572fce4673243b5365`)  
**Ship line:** branch `release/2.0.x` (this branch)  
**Dev line:** `main` (R&D; may be unstable)  
**Parked WIP:** `wip/echarts-theme-polish`  
**Strategy:** Mode A — freeze + release branch

## Cherry-picks applied (toward v2.0.6)

| Commit | Summary | Status |
|--------|---------|--------|
| `cb27301471` | python session lifecycle | Applied |
| `2ad14e6af5` | python SQL/report safe commit | Applied |
| `9532b6f1ab` | ModalTrigger / antd6 / chart type gate | Applied (resolved test file add) |
| `af617878e3` | Select/shared component types | Applied (minor test conflict) |
| `7878863d9f` | guided chart suggestions copy | Applied |
| `0bb35b3d99` | type-safety + genai fingerprint | **Skipped** — pulls GenAI pages/settings not on baseline |

Frontend unit tests: ModalTrigger + Tooltip **passed**.  
Python unit tests (session lifecycle / stability guards / base command / decorators): **31 passed**.

## Why this branch exists

After v2.0.5, `main` accumulated ~62 commits (~357 files) in roughly one day:
GenAI/authoring, phase-6 UX, MCP changes, session fixes, Dependabot, and
experimental ECharts chart-style work. Local installs also drifted
(antd 5 vs 6, react-router 6 vs 7), which made the tree feel broadly broken.

**Strategy:** freeze product shipping on a release line cut from the last
known-good tag. Re-admit changes only as reviewed cherry-picks.

```
ax-bi-desktop-v2.0.5  →  release/2.0.x  →  ax-bi-desktop-v2.0.6 (next ship)
                              ↑
                    cherry-picks only when green
                              ↑
main (AI / MCP / UX R&D)
```

## Rules for this branch

1. **No feature trains.** Only bugfixes that restore v2.0.5-class behavior or
   proven critical fixes cherry-picked from `main`.
2. **Install with `npm ci`** in `ax-bi-frontend` (never hand-edit lock casually).
3. **No Dependabot auto-merge** onto this branch.
4. **Next desktop/web tag** only from `release/2.0.x` after smoke checklist green.
5. Incomplete work stays on feature/WIP branches (e.g. `wip/echarts-theme-polish`).

## Smoke checklist (before any tag)

| Flow | Pass |
|------|------|
| Backend health / app boot | |
| Login + session persist (web + desktop if shipping desktop) | |
| Open example dashboard | |
| Edit + save dashboard | |
| Explore: simple chart | |
| SQL Lab: simple query | |
| Desktop local runtime / deep link (desktop ship only) | |

## Immediate environment reset (local)

```bash
git checkout release/2.0.x
git reset --hard origin/release/2.0.x   # after first push
cd ax-bi-frontend
rm -rf node_modules
npm ci
# expect: antd@6.x, react-router-dom@7.x, react-redux@9.x
node -p "require('antd/package.json').version"
node -p "require('react-router-dom/package.json').version"
```

## Related branches

| Branch | Purpose |
|--------|---------|
| `release/2.0.x` | Ship line = v2.0.5 + proven fixes only |
| `main` | Continue R&D; do not treat as ship until gated |
| `wip/echarts-theme-polish` | Parked chart-style UX polish (swatches, live preview) |

See also: [`docs/recovery-2.0.x-triage.md`](docs/recovery-2.0.x-triage.md)
for commit-by-commit re-admission decisions.
