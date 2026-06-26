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

# ADR: Simplify the UX by Progressive Disclosure, Not by Removal

> **Related documents:**
> [PRD](ux-simplification-prd.md) ·
> [Technical Specification](ux-simplification-tech-spec.md) ·
> [GenAI BI ADR](genai-bi-adr.md)

## Status

Proposed

## Context

User feedback is that the product is too complicated and should feel as simple
as Power BI, Tableau, or Metabase. A hard constraint accompanies that feedback:
**keep the backend**. The backend is the product's strength (broad engine
support, governed semantic layer, RBAC/RLS, chart engine, MCP service); the
complexity is concentrated in how the frontend exposes it.

We must reduce perceived complexity without sacrificing the capabilities that
make the platform valuable to power users and that distinguish it from
consumer-only tools. The decision is *how* to simplify.

## Decision

Simplify the UX through **progressive disclosure and curation**, gated by
feature flags and aware of RBAC — **never by removing backend capability or
deleting features from the codebase**.

Concretely:

1. **Gate, don't delete.** Power-user and admin surfaces (SQL Lab, alerts and
   reports, RLS, CSS templates, themes, annotations, the full Explore control
   panel) remain fully present and reachable. Simplified mode relocates and
   de-emphasizes them; it never removes them.
2. **Simplified mode is opt-in and reversible.** A `SIMPLIFIED_NAV` feature flag
   (default off) controls Phase 1. With the flag off, behavior is unchanged.
   Subsequent phases add their own flags. No existing deployment changes until an
   operator opts in.
3. **Transform in the frontend, preserve the backend menu/source of truth.** The
   navigation is reshaped by a pure, unit-tested frontend transform over the
   existing menu data. The backend menu, routes, and permissions are untouched.
4. **The advanced path is always one click away.** Every simplified surface
   offers an explicit escape hatch to the full-power equivalent, with state
   preserved where applicable.
5. **The guided builder compiles to the existing query model.** Later phases add
   a guided chart builder, but it produces the same `query_context` the advanced
   panel produces. There is one query backend and one source of truth for query
   semantics.

## Considered Options

### Option 1: Strip the UI down to a consumer-only feature set

Remove or hard-disable power-user surfaces to force simplicity.

Pros: simplest possible default; least visual clutter.

Cons: destroys the platform's differentiation; alienates existing power users;
violates the "keep the backend / keep capability" constraint; irreversible churn
for existing deployments.

Decision: rejected.

### Option 2: Fork a separate "lite" frontend

Build a parallel, simplified frontend app beside the existing one.

Pros: clean separation; freedom to design from scratch.

Cons: doubles maintenance; two code paths drift; users on "lite" hit a wall when
they need a power feature; large up-front cost. Contradicts "keep the backend
and improve the existing UX".

Decision: rejected.

### Option 3: Progressive disclosure + curation, flag-gated (chosen)

Keep one frontend. Add simplified surfaces that sit in front of the full
experience, gated by flags and RBAC, with explicit escape hatches.

Pros: nothing is lost; reversible and low-risk; incremental and independently
shippable; existing deployments unaffected until opt-in; one source of truth for
queries and permissions.

Cons: requires disciplined "two altitudes, one engine" design; some duplicated
surface area (guided vs. advanced) to maintain.

Decision: accepted.

## Consequences

### Positive

- Default experience can approach Metabase/Power BI simplicity without losing
  power-user or enterprise capability.
- Zero behavior change for existing deployments until they opt in.
- Each phase ships independently behind its own flag; low blast radius.
- Complements the GenAI BI effort: deterministic click-path and AI prompt-path
  share the same governed backend.

### Negative

- Maintaining two altitudes (simple/advanced) adds surface area.
- Requires care to keep the guided builder and advanced panel semantically
  consistent.
- Role-aware defaults add configuration that must be documented.

## Security Implications

- Simplification is presentation-only. It must never widen access: relocating a
  menu entry must not bypass the RBAC checks that gate it. SQL Lab entries remain
  conditioned on `can_sqllab`; admin entries remain admin-gated.
- No new data-bearing route or permission is introduced by Phase 1.
- Per `SECURITY.md`, hiding a control in the UI is not a security boundary;
  authorization remains enforced at the route, command, and DAO layers
  regardless of what the simplified UI shows.

## Open Questions

- Should simplified mode be operator-global, per-role, or per-user preference
  first?
- Should curated viz sets be fork-default or operator-configurable?
- When both this effort and GenAI BI are enabled, what owns the home page?
