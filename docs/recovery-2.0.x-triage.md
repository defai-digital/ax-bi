# Post–v2.0.5 commit triage (re-admission board)

**Baseline:** `ax-bi-desktop-v2.0.5` (`0539100`)  
**HEAD of main at triage time:** `90acbb82cf`  
**Range:** `0539100..90acbb82cf` (~62 commits, ~23 non-Dependabot product commits)  
**Strategy:** Mode A (freeze + `release/2.0.x`)

Legend:

- **Keep** — candidate to cherry-pick onto `release/2.0.x` after smoke  
- **Hold** — stays on `main` / feature branch; flag-gate before ship  
- **Drop** — do not bring to release line (redo later if needed)

## Product commits (default classification)

| Commit | Summary | Default | Notes |
|--------|---------|---------|-------|
| `c4f1e14868` | feat(ai): establish analytics authoring contract | Hold | Large platform surface |
| `85352d93e4` | feat(genai): add admin-only optional LLM provider | Hold | Feature-flag before ship |
| `cee7ab32ee` | feat(ai): refine authoring capabilities; pin Rust 1.85 | Hold | |
| `7878863d9f` | fix(explore): clarify guided chart suggestions | Keep? | Small UX copy; validate alone |
| `64d7d4f2d0` | fix(ci): restore green Actions after Dependabot | Drop* | CI-only; re-apply if release CI needs |
| `44955457ab` | fix(ci): WebSocket checks on Node 24.16 | Drop* | |
| `a1e38ee180` | fix(ci): WebSocket workflow path filters | Drop* | |
| `c09cfad890` | fix(websocket): package-lock for TS 6 pin | Drop | Lock churn |
| `e1390e6025` | fix(docs): align docusaurus packages | Drop | Docs only |
| `f164f296f6` | fix(mcp): tool-call args, async session purge | Hold | MCP product-critical? reassess |
| `527e4ea380` | fix(mcp): API-key scope, rate-limit TTL | Hold | Security-ish; reassess for ship |
| `0a6ce1f507` | fix(mcp): cache max_item_size, isolation | Hold | |
| `765cc7fef8` | feat(genai): LLM admin audit, semantic assist | Hold | |
| `3e8679b66a` | fix(mcp): unused type-ignore | Drop | Trivial; comes with MCP if kept |
| `fd03826527` | feat(ui): phase 6 UX cleanup, drawers, responsive | Hold | Wide UI churn |
| `08645fc3da` | feat(genai): durable LLM settings + frontend TS | Hold | |
| `0bb35b3d99` | fix: type-safety + config_fingerprint cache | Keep? | Validate tests; may be real bugfix |
| `9532b6f1ab` | fix(ui): ModalTrigger, antd6 styles, chart type gate | Keep? | antd6 already on v2.0.5 line |
| `cb27301471` | fix(python): session lifecycle / transaction | Keep | Stability; run unit tests first |
| `2ad14e6af5` | fix(python): safe commit on SQL/report paths | Keep | Stability; run unit tests first |
| `af617878e3` | fix(ui): restore shared component type compatibility | Keep? | Type-only risk; smoke UI |
| `73a1465a40` | feat(ui): dashboard ECharts chart-style templates | Hold | New feature; incomplete polish |
| `90acbb82cf` | fix(ui): type-safe echarts_theme metadata | Hold | Depends on chart-style feature |

\* Revisit only if release CI is red without them.

## Dependabot / merge noise

All `chore(deps*)`, Dependabot merges, and bulk pip/npm pin syncs in the range:
**Drop** from the release line. Re-introduce later as deliberate, tested upgrades
on a dedicated PR against `release/2.0.x` or the next minor.

High-noise areas observed:

- docs docusaurus bumps  
- `ax-bi-websocket` typescript 6 → 7  
- frontend dev-dependencies group  
- multiple pip production/dev group bumps  

## Suggested cherry-pick order (after smoke of pure v2.0.5)

1. `cb27301471` — python session lifecycle  
2. `2ad14e6af5` — python safe commit  
3. `9532b6f1ab` — ModalTrigger / antd6 (if still reproduces on release)  
4. `0bb35b3d99` — fingerprint / type-safety (if tests prove value)  
5. `af617878e3` — shared component types (if needed for build)  
6. `7878863d9f` — explore copy (optional)

Each as its **own PR** into `release/2.0.x` with smoke checklist.

## Parked work (not for 2.0.6 unless explicitly scoped)

| Branch | Content |
|--------|---------|
| `wip/echarts-theme-polish` | Swatches select, live preview, hide internal palettes |
| `main` GenAI / authoring | Keep developing behind flags; no auto-ship |

## Definition of done for v2.0.6

- [ ] `release/2.0.x` smoke checklist 100% green  
- [ ] Only Keep cherry-picks landed (or zero cherry-picks = ship = v2.0.5 content)  
- [ ] `npm ci` clean on Node matching engines  
- [ ] Tag `ax-bi-desktop-v2.0.6` (and/or web release) from this branch  
- [ ] Product users pointed at the new tag, not floating `main`
