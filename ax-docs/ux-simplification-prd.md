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

# PRD: UX Simplification — A Simple BI Front Door Over a Powerful Backend

> **Related documents:**
> [ADR](ux-simplification-adr.md) ·
> [Technical Specification](ux-simplification-tech-spec.md) ·
> [GenAI BI PRD](genai-bi-prd.md) ·
> [GenAI BI Roadmap](../GENAI_BI_ROADMAP.md)

## Status

Proposed

## Summary

Users find the product too complicated. The feedback is explicit: keep the
backend, but make the experience as approachable as Power BI, Tableau, or
Metabase. This PRD defines a UX-only effort — **no backend capability is
removed** — that lowers the floor for non-technical users through progressive
disclosure, a guided chart-building path, and curated default surfaces, while
preserving every existing power-user capability behind an "Advanced" boundary.

This is the deterministic, click-driven complement to the
[GenAI BI](genai-bi-prd.md) effort. AI answers the "type a question" user; this
effort answers the "I want to click, not type" user. The product needs both.

## Problem

The backend is strong: broad SQL engine support, a governed semantic layer,
RBAC/RLS, a mature chart engine, and an MCP service. The complexity lives almost
entirely in how the UI exposes that power.

1. **The Explore control panel is the primary complexity sink.** 60+ control
   types across Data/Customize tabs, frequently 50–200 controls per chart. It is
   a configuration form, not a building experience.
2. **The data model leaks into the navigation.** Databases, Datasets, Saved
   Queries, and SQL Lab are four separate top-level destinations. A business
   user cannot tell which one they need.
3. **The flow is chart-first, not canvas-first.** Users build a chart → save it
   → then assemble a dashboard from saved charts. The two-step indirection is
   friction competitors do not impose.
4. **Admin and operator surfaces sit in the main chrome.** Row Level Security,
   CSS Templates, Themes, Annotations, Tasks, Roles, and Users all hang off the
   gear menu where every user sees them, even though most users never use them.
5. **The visualization gallery overwhelms.** 50+ chart types presented as a flat
   grid produces choice paralysis at the exact moment a new user is least
   equipped to choose.

## Goals

- Reduce time-to-first-chart and time-to-first-dashboard for a non-technical
  user.
- Present a default surface that feels comparable in simplicity to Metabase /
  Power BI.
- Preserve 100% of existing power-user capability behind progressive
  disclosure — nothing is deleted.
- Make every simplification opt-in and reversible via feature flags and role
  awareness, so existing deployments are unaffected until they choose otherwise.

## Non-Goals

- Removing or rewriting backend capabilities, APIs, or the semantic layer.
- Removing SQL Lab, alerts/reports, RLS, or any admin surface — these are
  relocated and gated, not deleted.
- Replacing the existing Explore control panel for power users. The guided
  builder is an additive default, not a replacement.
- Shipping the GenAI "Ask" experience, which is owned by the
  [GenAI BI PRD](genai-bi-prd.md). This PRD assumes the two land side by side.

## Personas

| Persona | Today's pain | What "simple" means for them |
| --- | --- | --- |
| **Business viewer** | Lands on a list of charts; doesn't know where to start. | A clear home with "Ask / Browse / Build"; never sees SQL or admin. |
| **Analyst (self-serve)** | Faces a 60-control panel to make a bar chart. | A guided "pick data → filter → summarize → visualize" path. |
| **Power analyst** | Wants the full control panel and SQL Lab. | Nothing taken away; one click to "Advanced". |
| **Admin / operator** | Admin items clutter everyone's menu. | A dedicated admin area; cleaner default nav for their users. |

## Market Comparison

| Tool | What makes it feel simple | Lesson adopted here |
| --- | --- | --- |
| **Metabase** | Guided "notebook" builder (pick data → filter → summarize → group → visualize); X-ray instant dashboards. | Guided builder as the default chart path; auto-generated starter dashboards. |
| **Power BI** | Build visuals directly on the canvas; NL Q&A box; quick-measure wizard. | Canvas-first dashboards; AI front door (GenAI PRD). |
| **Tableau** | "Show Me" recommends a viz from selected fields; drag-to-shelf. | Recommended-viz row replaces the flat gallery. |
| **ThoughtSpot** | Search is the primary interface; SpotIQ auto-insights. | Prompt/search as a home-page front door (GenAI PRD). |
| **Sigma** | Spreadsheet-like familiarity. | Lower the conceptual floor; hide engineering concepts. |

The convergence across leaders: **progressive disclosure + a low-floor entry
point + smart defaults**, with full power available but not in the user's face.

## Requirements

Requirements are phased so value ships incrementally and the lowest-risk work
lands first. Each phase is independently shippable and flag-gated.

### Phase 1 — Simplified Navigation (lowest risk, ships first)

- **P1-R1** A `SIMPLIFIED_NAV` feature flag (default off) controls all Phase 1
  behavior. With the flag off, navigation is byte-for-byte unchanged.
- **P1-R2** In simplified mode, the main navigation shows only consumer-facing
  destinations: Dashboards, Charts, and Data. Power-user destinations (SQL Lab,
  Saved Queries) are relocated into a grouped menu rather than occupying the top
  bar.
- **P1-R3** Relocation respects existing RBAC: a user without `can_sqllab` never
  sees SQL entries regardless of mode (unchanged behavior).
- **P1-R4** Admin/operator surfaces remain grouped under Settings (existing
  behavior) and are visually separated so non-admins see a clean menu.
- **P1-R5** No destination becomes unreachable; demoted items remain accessible
  via their relocated menu group and their direct URLs.

### Phase 2 — Curated Create & Viz Gallery

- **P2-R1** A unified "New" entry exposes Chart / Dashboard (and, when GenAI is
  enabled, Ask).
- **P2-R2** The visualization gallery presents a curated default set (≈12–15
  common types: table, big number, bar, line, area, pie, scatter, pivot, map)
  with the long tail behind "More charts".
- **P2-R3** Curation is configuration-driven, not hard-coded per plugin.

### Phase 3 — Guided Query Builder

- **P3-R1** A stepped builder (pick data → filter → summarize → group → sort →
  visualize) is the default chart-creation surface in simplified mode.
- **P3-R2** The builder compiles to the existing `query_context`; no new query
  backend is introduced.
- **P3-R3** A persistent "Switch to advanced" affordance drops into today's full
  control panel with state preserved.

### Phase 4 — Auto-Insights ("X-ray") and Build-on-Canvas

- **P4-R1** From a dataset, a user can generate a starter dashboard from existing
  metrics/dimensions in one click.
- **P4-R2** Users can add a new chart directly onto a dashboard canvas without
  the save-chart-first detour.

## Success Metrics

- Time-to-first-chart for a new analyst (target: meaningful reduction vs. the
  current Explore flow).
- Proportion of charts created via the guided builder vs. the advanced panel.
- Number of distinct top-level nav destinations a default (non-admin) user sees.
- Task-completion rate in moderated usability tests for "build a bar chart of X
  by Y" and "assemble a 3-chart dashboard".
- No regression in power-user task completion (advanced path remains one click
  away).

## Rollout

- Every phase is gated by a feature flag, default off. Existing deployments are
  unaffected until an operator opts in.
- Simplified mode can be enabled globally by an operator or, in a later
  iteration, defaulted by role (e.g., Gamma sees simple, Alpha/Admin see full).
- Documentation in `docs/` is updated per phase; any default-changing behavior is
  recorded in `UPDATING.md`.

## Risks

| Risk | Mitigation |
| --- | --- |
| Simplification hides a feature a user needs. | Gate-not-delete: everything stays reachable via Advanced and direct URL. Flag-gated rollout. |
| Two builders (guided + advanced) drift. | Guided builder compiles to the same `query_context`; advanced panel remains the single source of truth for query semantics. |
| Operators perceive churn. | Default off; no behavior change unless explicitly enabled. |
| Scope creep into backend. | Non-goal stated explicitly; ADR records the UX-only boundary. |

## Open Questions

- Should simplified mode be operator-global, per-role, or per-user preference in
  the first release?
- Should the curated viz set be fork-default or operator-configurable from the
  start?
- How should the guided builder and the GenAI "Ask" front door share the home
  page real estate?
