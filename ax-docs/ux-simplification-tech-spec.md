<!--
Licensed to the Apache Software Foundation (ASF) under one
or more contributor license agreements.  See the NOTICE file
distributed with this work for additional information
regarding copyright ownership.  The ASF licenses this file
to you under the Apache License, Version 2.0 (the
"License"); you may not use this file except in compliance
with the License.  You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing,
software distributed under the License is distributed on an
"AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
KIND, either express or implied.  See the License for the
specific language governing permissions and limitations
under the License.
-->

# Technical Specification: UX Simplification

> **Related documents:**
> [PRD](ux-simplification-prd.md) ·
> [ADR](ux-simplification-adr.md) ·
> [GenAI BI Tech Spec](genai-bi-tech-spec.md)

## Overview

This spec describes the implementation of the UX simplification effort defined in
the [PRD](ux-simplification-prd.md) under the principle established in the
[ADR](ux-simplification-adr.md): simplify by progressive disclosure and curation,
flag-gated, never by removing capability. The backend is untouched except for
adding feature-flag definitions.

The work is phased. **Phase 1 (Simplified Navigation) is specified in
implementation detail and is the first deliverable.** Later phases are specified
at design level and refined when scheduled.

## Phase 1 — Simplified Navigation

### Goal

When `SIMPLIFIED_NAV` is enabled, the top navigation presents only
consumer-facing destinations (Dashboards, Charts, Data). Power-user destinations
(SQL Lab, Saved Queries / Query History) are relocated into a single grouped
"Advanced" submenu instead of occupying the top bar. With the flag off,
navigation is byte-for-byte unchanged.

### Feature flag

Add `SIMPLIFIED_NAV` (default `False`, lifecycle: development) in two places that
already mirror each other:

- Backend: `superset/config.py` `DEFAULT_FEATURE_FLAGS` (development block).
- Frontend enum: `superset-frontend/packages/superset-ui-core/src/utils/featureFlags.ts`
  `FeatureFlag` (kept alphabetically sorted), value `'SIMPLIFIED_NAV'`.

Feature flags are serialized to `window.featureFlags` and read via
`isFeatureEnabled(FeatureFlag.SimplifiedNav)`.

### Where the transform lives

Navigation data originates from the Flask-AppBuilder menu and is already
post-processed in the frontend by `MenuWrapper` in
`superset-frontend/src/features/home/Menu.tsx`. `MenuWrapper` splits backend menu
items into:

- `cleanedMenu` — top-level nav (Dashboards, Charts, Datasets, SQL).
- `settings` — items named `Data`, `Security`, `Manage` (the gear dropdown).

Phase 1 inserts one pure transform, `simplifyMenuData`, immediately before
`MenuWrapper` constructs the final `MenuData`. The transform operates on the
already-split structure and is independent of React.

### `simplifyMenuData` contract

New module: `superset-frontend/src/features/home/simplifyMenu.ts`

```ts
// Pure, framework-free. No RBAC logic here — items arriving in `menu` have
// already passed backend permission filtering, so relocation cannot widen access.
export const DEMOTED_NAV_LABELS = ['SQL'] as const;

export function simplifyMenuData(
  menu: MenuObjectProps[],
  enabled: boolean,
): { menu: MenuObjectProps[]; demoted: MenuObjectProps[] };
```

Behavior:

- `enabled === false` → returns `{ menu, demoted: [] }` unchanged (referentially
  safe; callers fall back to existing behavior).
- `enabled === true` → partitions `menu` into kept items and demoted items by
  matching the top-level item's FAB `name` or `label` against
  `DEMOTED_NAV_LABELS`. Returns the kept items as `menu` and the matched items as
  `demoted`.

Matching is by stable identifier (`name` preferred, `label` fallback) so it is
resilient to translation. Because partitioning is the only operation, no item is
ever dropped: every demoted item is returned for re-attachment.

### Wiring into `MenuWrapper`

In `MenuWrapper` (`Menu.tsx`), after `cleanedMenu`/`settings` are built:

```ts
const simplifiedNav = isFeatureEnabled(FeatureFlag.SimplifiedNav);
const { menu: primaryMenu, demoted } = simplifyMenuData(cleanedMenu, simplifiedNav);

newMenuData.menu = primaryMenu;
newMenuData.settings = demoted.length
  ? [...settings, { label: t('Advanced'), name: 'Advanced', childs: flattenChilds(demoted) }]
  : settings;
```

The demoted items' children (e.g., Saved Queries, Query History) are flattened
into an "Advanced" settings group so they remain reachable from the Settings
dropdown. Direct URLs (`/sqllab`, `/savedqueryview/list/`) are unaffected.

### RBAC invariant

`simplifyMenuData` performs no permission checks and must not. Items reaching it
have already been filtered by FAB according to the user's roles, so a user
without `can_sqllab` has no SQL item to demote. Relocation is presentation-only
and cannot widen access (see [ADR](ux-simplification-adr.md) Security
Implications and `SECURITY.md`).

### Testing

- Unit: `superset-frontend/src/features/home/simplifyMenu.test.ts`
  - flag off → input returned unchanged, `demoted` empty.
  - flag on → SQL item removed from `menu`, present in `demoted`.
  - flag on with no SQL item (e.g., Gamma) → `menu` unchanged, `demoted` empty.
  - no item is lost: `menu ∪ demoted` equals the input set.
- Type checking: `npm run type`.
- Existing `Menu` component tests must continue to pass with the flag off
  (default), proving zero behavior change.

### Out of scope for Phase 1

No changes to routes, backend menu construction, permissions, or the Explore /
SQL Lab pages themselves. Only the presentation/grouping of existing nav entries
changes, and only when the flag is on.

## Phase 2 — Curated Create & Viz Gallery (design)

- Curated viz set defined as configuration (a list of `vizType` keys) consumed by
  `VizTypeGallery`; remaining plugins move behind a "More charts" disclosure.
- Unified "New" entry reuses the existing `RightMenu` "new-dropdown" structure in
  `RightMenu.tsx`, adding an "Ask" item when GenAI flags are enabled.

## Phase 3 — Guided Query Builder (implemented)

Gated by the `GUIDED_CHART_BUILDER` feature flag (default off; added to
`config.py` and the frontend `FeatureFlag` enum).

### Module

`superset-frontend/src/explore/components/GuidedBuilder/`

- `types.ts` — `GuidedIntent` (vizType, measures, dimensions, filters, rowLimit),
  `GuidedFilter`, and the declarative `VizDescriptor`.
- `vizDescriptors.ts` — the curated viz table. Each entry declares how that viz
  consumes measures/dimensions, verified against the plugin `controlPanel`:
  - Table → `metrics` (array) + `groupby`, plus `query_mode: 'aggregate'`.
  - Big Number (`big_number_total`) → `metric` (single), no dimensions.
  - Pie → `metric` (single) + `groupby`.
  - Bar / Line / Area (echarts timeseries) → `metrics` (array); first dimension
    routes to `x_axis`, the rest to `groupby`.
- `compileIntent.ts` — **pure** `GuidedIntent → Partial<form_data>`, including
  `buildAdhocFilter` which sets both `operator` and `operatorId` (from
  `src/explore/constants`) with correct comparator arity.
- `intentFromFormData.ts` — **pure** reverse read; extracts only the
  guided-representable parts (saved metrics, plain columns, simple filters) and
  ignores adhoc/SQL objects, which remain editable in the advanced panel.
- `GuidedBuilder.tsx` — the stepped UI (visualization → measures → group by →
  filters → row limit). Each edit dispatches `setControlValue` for every
  compiled key (viz_type first) so Redux `form_data` stays authoritative; an
  "Update chart" button calls the existing `onQuery` (which dispatches
  `triggerQuery`). A "Switch to advanced" button hands off to the full panel.

### Wiring

`ExploreViewContainer/index.tsx` adds a `builderMode` state and renders
`<GuidedBuilder>` in the controls column when the flag is on and the current viz
type is guided-supported (else `<ConnectedControlPanelsContainer>`). Both consume
the same `props.actions`, `form_data`, and `datasource`, so query semantics have a
single source of truth. No backend query path is introduced.

### Tests

`compileIntent.test.ts` and `intentFromFormData.test.ts` cover each viz
descriptor, the filter operator arities (equals / IN-splitting / value-less), and
a compile∘read round-trip.

### Known limitations (follow-ups)

- Guided mode represents **saved metrics and plain columns** only; adhoc metrics,
  adhoc columns, and SQL filters are preserved in `form_data` but edited via
  Advanced.
- **Sorting** is intentionally omitted from v1 (the sort control key is
  viz-specific: table uses `timeseries_limit_metric`+`order_desc`, pie uses
  `sort_by_metric`). Sorting is available in Advanced.
- "Switch to advanced" is one-way within a session; guided mode is restored on
  reload for supported viz types. A reverse in-session toggle is a follow-up
  (avoided here to keep `ControlPanelsContainer` untouched).

## Phase 4 — Auto-Insights and Build-on-Canvas (design)

- "X-ray": a command that, given a dataset, selects a few metrics/dimensions from
  the semantic layer and composes a starter dashboard via existing chart and
  dashboard creation commands. Overlaps with GenAI `compose_dashboard`; share the
  composition layer where possible.
- Build-on-canvas: allow `SliceAdder` / dashboard edit mode to host an inline
  Explore for a brand-new chart, removing the save-chart-first step.

## Rollout & Compatibility

- All phases default off. `UPDATING.md` records any future default change.
- `docs/` updated per phase.
- No migration required for Phase 1 (no schema or API change).
