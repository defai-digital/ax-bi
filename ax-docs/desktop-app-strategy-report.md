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

# Report: Desktop App Strategy For AX-BI

> **Related documents:**
> [UX Simplification PRD](ux-simplification-prd.md) ·
> [GenAI BI PRD](genai-bi-prd.md) ·
> [GenAI BI Roadmap](../GENAI_BI_ROADMAP.md)

## Status

Proposed

## Executive Summary

Users have asked for AX-BI to feel more like a desktop application on Windows
and macOS. Embedding the existing web application in Electron is one possible
answer, but it should not be the default first step.

The recommended strategy is:

1. Improve the hosted web application so it behaves like a desktop-grade
   workspace.
2. Add installability through Progressive Web App capabilities where browser and
   operating system support is sufficient.
3. Build a thin desktop shell only when native operating system integration
   creates user value that the browser cannot provide.
4. Prefer Tauri or native WebView wrappers for a thin shell; choose Electron
   only when its mature Chromium-based desktop ecosystem is specifically needed.

AX-BI is a server-backed BI product. A desktop wrapper does not, by itself,
solve the user experience problems that make a product feel unlike a desktop
application. The highest-value work is in navigation, workspace persistence,
keyboard ergonomics, window behavior, notifications, exports, and
task-oriented flows.

## User Feedback Interpreted

The feedback "make it more like a desktop app" can mean several different
things:

- The app should launch from Start Menu, Dock, Launchpad, or Spotlight.
- The app should run in its own standalone window instead of a browser tab.
- The app should remember workspace state, open dashboards, panes, filters, and
  recent items.
- The app should have reliable keyboard shortcuts and command-style navigation.
- Exports, downloads, and local files should feel integrated with the operating
  system.
- Notifications should use native notification surfaces.
- Authentication should feel stable and enterprise-friendly.
- The app should feel faster and less web-page-like during navigation.

Only the first two are directly solved by wrapping the app. The rest are product
and frontend architecture work that should benefit all users, including browser
users.

## Recommendation

### Primary Recommendation: Desktop-Grade Web App First

AX-BI should first invest in a desktop-grade web experience:

- Add a web app manifest, installable icons, branded window title, and standalone
  display mode.
- Improve persistent workspace behavior: recently opened dashboards, pinned
  assets, saved filter state, panel widths, selected tabs, and interrupted
  workflows.
- Add a command palette for navigation and actions.
- Make keyboard shortcuts consistent across dashboards, Explore, SQL Lab, and
  future GenAI flows.
- Make export and download flows predictable, with clear progress and failure
  handling.
- Use native browser notifications for reports, long-running queries, and AI job
  completion where permission is granted.
- Continue the UX simplification work so business users see a focused front
  door instead of an administrative web console.

This creates value regardless of whether AX-BI later ships a desktop wrapper.

### Secondary Recommendation: Thin Desktop Shell

If users still need a downloadable desktop application, AX-BI should add a thin
shell that loads the hosted AX-BI instance. The shell should be treated as a
client, not as a local Superset distribution.

Good reasons to ship a thin shell:

- Enterprise users want a signed Windows/macOS app in managed device catalogs.
- The product needs deep links such as `axbi://dashboard/{uuid}`.
- The product needs native notifications, tray integration, or single-instance
  behavior.
- The product needs better control over external link handling, downloads, and
  app window lifecycle.
- Customers want a branded desktop presence while keeping the server deployment
  centralized.

The thin shell should avoid duplicating business logic. Superset, AX-BI
features, RBAC, RLS, MCP service integration, chart rendering, and GenAI
workflows should remain server-backed and governed by the existing application.

### Electron Recommendation

Electron is viable but should be selected deliberately. It is appropriate when
AX-BI needs:

- A consistent bundled Chromium runtime across Windows and macOS.
- Mature cross-platform packaging, signing, updater, crash reporting, and
  desktop ecosystem support.
- Rich native integrations that are easier to implement in Electron's ecosystem.
- Extensive control over browser behavior that is difficult to guarantee with
  platform WebViews.

Electron is not ideal when the shell mostly opens a trusted web app and exposes
only a few native affordances. In that case, its application size, update
surface, and security obligations are likely higher than necessary.

## Options Considered

### Option 1: Progressive Web App

Use installable web app capabilities so AX-BI can run in a standalone window
with app icons and launch surfaces.

Pros:

- Lowest implementation and maintenance cost.
- One frontend codebase.
- No separate desktop release process.
- Benefits all users, including browser-only users.
- Easier enterprise security posture than distributing a native wrapper.

Cons:

- Native integration is limited compared with a desktop shell.
- Support varies by browser and operating system.
- Enterprise app-catalog distribution may be less familiar for some customers.
- No direct control over browser engine version.

Decision: accepted as the first implementation path.

### Option 2: Tauri Thin Shell

Build a lightweight native shell using the operating system WebView and a small
allowlisted native bridge.

Pros:

- Smaller application size than Electron.
- Uses platform WebView rather than bundling Chromium.
- Good fit for a thin client that loads a hosted AX-BI instance.
- Strong permission model for native capabilities.

Cons:

- WebView behavior can vary across operating systems.
- Ecosystem is smaller than Electron's.
- Complex desktop requirements may require more native-platform work.

Decision: preferred desktop-shell option for a thin AX-BI client.

### Option 3: Electron Thin Shell

Build an Electron application that loads the hosted AX-BI web app.

Pros:

- Mature desktop application ecosystem.
- Consistent Chromium runtime across platforms.
- Strong packaging, auto-update, native module, and debugging story.
- Well understood by many frontend teams.

Cons:

- Larger application footprint.
- Bundles a browser runtime that must be kept updated.
- Requires careful security hardening, especially for remote content.
- Can encourage desktop-specific behavior that forks the web experience.

Decision: acceptable only when Electron-specific strengths are required.

### Option 4: Fully Bundled Local Desktop AX-BI

Package Superset, AX-BI customizations, Python, database drivers, metadata
storage, browser runtime, and update machinery into a local desktop product.

Pros:

- Potential offline or local-only story.
- Could appeal to single-user analyst workflows.

Cons:

- High packaging and support complexity.
- Hard database driver compatibility problem.
- Hard upgrade and migration story.
- More complicated security posture for secrets, metadata, and local files.
- Conflicts with AX-BI's server-backed governance, RBAC, RLS, and MCP
  architecture.

Decision: rejected unless offline local BI becomes a separate product mandate.

## Proposed Architecture

```text
Windows/macOS launcher
  -> PWA standalone window or thin native shell
  -> Hosted AX-BI web application
  -> Existing Superset APIs, commands, DAOs, RBAC, RLS
  -> Existing MCP service for GenAI and agent workflows
```

For a native shell:

```text
Desktop shell
  -> Trusted AX-BI origin allowlist
  -> Minimal native bridge
       - open external URL
       - download/export helper
       - native notification helper
       - deep link handler
       - app menu/window controls
  -> No direct database credentials
  -> No bypass of Superset auth or permissions
```

The shell should never become a second backend. It should not implement BI
permissions, query execution, semantic metadata, chart generation, or dashboard
mutation outside Superset and the AX-BI server.

## Security Requirements

Any desktop strategy must preserve the Superset and AX-BI security model:

- All data access runs as the authenticated Superset principal.
- RBAC, RLS, dataset permissions, dashboard permissions, and MCP privacy
  controls remain server-enforced.
- The desktop shell must not store database credentials.
- The shell must not expose broad native APIs to web content.
- Only trusted AX-BI origins may be loaded.
- Navigation to untrusted origins must open in the system browser, not inside
  the privileged app window.
- IPC or native bridge calls must be allowlisted, typed, and validated.
- Session tokens and cookies must use the same security rules as the web app.
- Logs, crash reports, and telemetry must not include query results, secrets, or
  prompt contents unless explicitly governed.

For Electron specifically:

- Keep Electron updated.
- Disable Node.js integration for renderer content.
- Enable context isolation and sandboxing.
- Use a strict content security policy.
- Validate all IPC messages.
- Restrict navigation and new-window behavior.
- Do not load arbitrary remote content in privileged windows.

## Product Requirements

Desktop feel should be defined by product behavior, not by packaging alone.

Minimum desktop-grade UX requirements:

- Standalone launch surface with AX-BI branding.
- Fast return to the user's previous workspace.
- Recent dashboards, charts, datasets, and queries.
- Pinned workspaces or favorites.
- Command palette for global navigation and actions.
- Keyboard shortcuts for common dashboard, Explore, and SQL Lab operations.
- Clear long-running query and report progress.
- Native-feeling export and download flows.
- Deep-link support for dashboards, charts, datasets, and GenAI flows.
- Consistent empty, loading, offline, and reconnect states.

Nice-to-have requirements:

- Native notification integration.
- System tray or menu bar integration for background jobs.
- App-level update notifications for desktop shell releases.
- Admin-configurable default AX-BI instance URL.
- Enterprise policy controls for allowed origins and auth domains.

## Implementation Plan

### Phase 1: Desktop-Grade Web Foundation

- Add web app manifest and installability assets.
- Audit top-level navigation, dashboard, Explore, and SQL Lab for standalone
  window behavior.
- Add persistent workspace state for high-value flows.
- Add command palette and keyboard shortcut registry.
- Improve export, download, and long-running job feedback.

### Phase 2: PWA Pilot

- Pilot installable AX-BI with internal Windows and macOS users.
- Validate SSO behavior, session persistence, downloads, notifications, and
  deep links.
- Measure whether PWA installability satisfies the user feedback without a
  native shell.

### Phase 3: Thin Shell Prototype

- Prototype Tauri as the default thin-shell candidate.
- Load only configured trusted AX-BI origins.
- Implement deep links, native notifications, and controlled external link
  handling.
- Compare Tauri against Electron only if WebView behavior or ecosystem gaps
  block the required experience.

### Phase 4: Enterprise Distribution

- Add signed installers and notarized macOS artifacts.
- Define managed configuration for default instance URL and allowed origins.
- Add auto-update policy if a native shell ships.
- Document deployment and support boundaries.

## Decision Criteria

Choose PWA-only if:

- Users mainly want launcher presence and standalone windows.
- Browser-based SSO and downloads behave well enough.
- Enterprise distribution does not require a native installer.

Choose Tauri if:

- Users need a signed desktop app with a small native bridge.
- Native needs are limited to deep links, notifications, downloads, app menus,
  and window lifecycle.
- Platform WebView differences are acceptable.

Choose Electron if:

- AX-BI needs consistent Chromium behavior across platforms.
- Native integration requirements exceed what Tauri/WebView can deliver
  efficiently.
- The team is prepared to own Electron update, packaging, and security hardening
  as a first-class product surface.

Reject local bundled AX-BI unless:

- Offline local BI becomes a required product direction.
- The product accepts a separate support model for local servers, database
  drivers, metadata migrations, and local secret handling.

## Risks

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Packaging is mistaken for UX improvement. | Users still perceive the app as web-like. | Define desktop success around workflows, persistence, shortcuts, and performance. |
| Desktop shell forks behavior from the web app. | Higher maintenance cost and inconsistent support. | Keep shell thin; put product logic in the web app and server. |
| Electron increases security and update burden. | Larger attack and maintenance surface. | Prefer PWA/Tauri first; harden Electron if selected. |
| Platform WebView differences affect Tauri. | Inconsistent rendering or auth behavior. | Prototype against key customer environments before committing. |
| Enterprise auth behaves differently in standalone windows. | Login friction or failed SSO flows. | Test OIDC/SAML flows early with real customer identity providers. |

## Open Questions

- Do target customers require managed desktop app distribution through Intune,
  Jamf, or similar tools?
- Which identity providers and browser policies must be supported?
- Is offline usage a real requirement or a proxy for faster startup and better
  persistence?
- Which native integrations are mandatory for the first desktop release?
- Should the desktop shell support multiple AX-BI instances or a single
  operator-configured instance?

## External References

- [Progressive Web App installation](https://web.dev/learn/pwa/installation)
- [Electron security checklist](https://www.electronjs.org/docs/latest/tutorial/security)
- [Tauri security model](https://v2.tauri.app/security/)
- [Microsoft WebView2 distribution](https://learn.microsoft.com/en-us/microsoft-edge/webview2/concepts/distribution)
