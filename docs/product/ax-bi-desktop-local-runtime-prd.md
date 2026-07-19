<!--
Licensed to the Apache Software Foundation (ASF) under one or more
contributor license agreements. See the NOTICE file distributed with
this work for additional information regarding copyright ownership.
The ASF licenses this file to You under the Apache License, Version 2.0
(the "License"); you may not use this file except in compliance with
the License. You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
-->

# PRD: AX BI Desktop Local Runtime Reliability and First-Run UX

## Overview

AX BI Desktop should provide a reliable, layperson-friendly local analytics experience on macOS. The current Homebrew/Desktop flow can install and run the Docker stack, but several open issues make the product feel broken: dependency detection can be wrong, startup failures can be stale or misleading, first-run login credentials are hidden, dashboard pages can flood Action Logs, uploaded datasets can fail to render columns in Explore, and the About version can conflict with the installed Desktop version.

This PRD consolidates issues #1-#8 in `defai-digital/homebrew-ax-bi` into one implementation plan.

## Source Issues

- #1: AX BI Desktop reports Colima/Docker/Compose missing even when Homebrew dependencies are installed.
- #2: Desktop webview loops back to login after successful local admin login.
- #3: Default Colima profile resources are too low for local runtime worker.
- #4: First-run AX BI Desktop login flow hides generated admin credentials.
- #5: Uploaded dataset has columns in API but Explore UI shows Metrics/Columns as 0 of 0.
- #6: Desktop reports db unhealthy even though local AX BI stack is healthy.
- #7: Action Logs grow rapidly from repeated dashboard filter-state POSTs.
- #8: Desktop 2.0.4 runs web UI that still reports version 2.0.2.

## Goals

1. Make local runtime startup deterministic, transparent, and recoverable.
2. Make first-run onboarding possible without terminal access or hidden files.
3. Ensure uploaded datasets are immediately usable in Explore.
4. Prevent background dashboard behavior from flooding Action Logs.
5. Make Desktop/runtime version information understandable and accurate.

## Non-Goals

- Replace Colima with Docker Desktop as the primary runtime.
- Redesign AX BI's full authentication model for hosted/team deployments.
- Redesign Explore or Dashboard builder beyond the specific defects listed here.
- Add cloud account signup to the local-only Desktop flow.

## Personas

### First-Time Local User

Installs AX BI with Homebrew or the Desktop app and expects to open the app, start local AX BI, and begin uploading files without knowing Docker, Colima, `.env` files, or generated passwords.

### Technical Evaluator

Can use terminal commands, but expects Desktop status to match actual runtime state and wants clear diagnostics when something fails.

### Product Support Engineer

Needs enough diagnostics in Desktop to distinguish missing dependencies, low resources, port conflicts, transient health checks, and real container failures.

## Problem Statements

### Runtime Detection and Startup

Desktop can report missing tools even when `colima`, `docker`, and `docker-compose` exist. It can also show a permanent failure that `axbi-db-1` is unhealthy after the Compose stack becomes healthy and the web endpoint responds.

### First-Run Login

The local runtime generates an admin password but stores it only in `~/Library/Application Support/com.axbi.desktop/local-runtime/.env`. Users see a login page with no signup flow and no visible credentials.

### Webview Session Handling

The Desktop webview can accept valid credentials server-side but loop back to login, suggesting cookie/session persistence problems in the embedded webview.

### Dataset Explore Rendering

After upload succeeds and backend metadata/API return columns and metrics, Explore can still render Metrics and Columns as `0 of 0`, blocking chart creation.

### Action Log Flooding

Viewing a dashboard can generate many `DashboardFilterStateRestApi.post` records per minute, often for unchanged or empty filter state.

### Version Confusion

Desktop/Homebrew can report `2.0.4` while the running web runtime reports `2.0.2`, making users believe the update failed.

## Requirements

### R1. Robust Dependency Detection

Desktop must detect required tools using a deterministic binary resolution strategy:

- Check configured path overrides, if present.
- Check `/opt/homebrew/bin`, `/usr/local/bin`, and the inherited PATH.
- Execute `colima version`, `docker --version`, and `docker compose version`.
- Show the exact resolved binary paths and versions in Settings.

Acceptance criteria:

- If all tools are installed and executable, Desktop does not show "Install missing tools first."
- If a tool is missing, Desktop names the missing tool and shows the command to install it.
- A refresh/retry action re-runs detection and clears stale missing-tool state.

### R2. Startup State Machine and Health Reconciliation

Desktop must treat Docker startup as a state machine, not a one-shot command result.

States:

- Not configured
- Checking dependencies
- Starting Colima
- Pulling images
- Starting containers
- Waiting for health
- Running
- Failed

Health reconciliation requirements:

- If `docker compose up --wait` exits non-zero, Desktop must re-check final container states for a short grace period.
- If `ax-bi` responds at `/health` or redirects `/` to `/ax-bi/welcome/`, Desktop must prefer the final healthy state over stale command stderr.
- Failed status must include the failing service, last health output, and a retry button.

Acceptance criteria:

- A transient `db unhealthy` compose failure does not remain visible if `axbi-db-1` becomes healthy and AX BI responds.
- The main screen and Settings show the same current runtime state.
- Desktop can recover from a previous failure without requiring cache clearing or app reinstall.

### R3. Port Conflict Handling

Desktop must detect when default ports are occupied before starting or opening AX BI.

Required ports:

- AX BI web: default `31423`
- MCP: default `31421`
- AX services: default `31424`

Acceptance criteria:

- If a port is occupied, Desktop shows the process/container using it.
- Desktop either offers to choose an available port or clearly tells the user what must be stopped.
- The final chosen URL is displayed and copied into the webview/navigation target.

### R4. Colima Resource Defaults and Preflight

Desktop-created Colima profiles must be provisioned with resources sufficient for the AX BI stack.

Minimum recommended default:

- CPU: 4
- Memory: 8 GB
- Runtime: Docker

Acceptance criteria:

- New Desktop-created profiles use the recommended default or higher.
- Existing low-resource profiles trigger a warning before startup.
- Worker OOM/unhealthy states are mapped to an actionable "Increase Colima memory" message.

### R5. First-Run Local Admin Onboarding

Desktop must provide a visible path into the first local instance.

Approved implementation options:

- Prompt user to create the local admin password during first-run setup.
- Display generated local credentials with copy buttons.
- Use secure local-only auto-login from Desktop into the local web runtime.

Minimum requirement:

- The user must not need to open `.env` or use terminal commands to discover credentials.

Acceptance criteria:

- Fresh install starts local runtime and gives the user a clear login/setup path.
- The username and password/token are never logged in plaintext.
- Reset/reveal/copy credential actions are available from Settings with appropriate confirmation.

### R6. Desktop Webview Session Reliability

The embedded webview must preserve authenticated local sessions.

Acceptance criteria:

- After valid credentials are accepted, the webview reaches `/ax-bi/welcome/`.
- Session cookies persist across in-app navigation and page reload.
- If cookies are blocked or invalid, Desktop shows a session diagnostic instead of "Invalid username or password."
- Browser login and Desktop webview login behave consistently for the same local runtime.

### R7. Uploaded Dataset Explore Usability

Explore must render uploaded dataset columns and metrics immediately after upload when backend metadata/API contain them.

Acceptance criteria:

- After successful `POST /api/v1/database/auto_upload/` with `201`, Explore displays the created dataset's columns and default metric.
- If the Explore API returns columns but the sidebar is empty, frontend state refreshes or shows a recoverable error.
- Service worker/cache state cannot permanently hide valid dataset metadata.
- Regression test covers uploaded file -> dataset -> Explore sidebar columns.

### R8. Action Log Noise Reduction

AX BI must avoid logging repeated dashboard filter-state saves when there is no meaningful user action.

Acceptance criteria:

- `DashboardFilterStateRestApi.post` is not logged when the payload is unchanged or empty.
- Dashboard viewing does not create more than 5 action-log rows per minute while idle.
- Meaningful filter changes remain auditable.
- Existing log table remains queryable; no migration is required to delete old rows, though a cleanup tool may be added separately.

### R9. Version Clarity

The About dialog and Settings must clearly distinguish Desktop launcher version from web runtime version.

Acceptance criteria:

- Desktop displays Desktop version from app bundle/cask.
- Web runtime displays runtime package/image version.
- If versions intentionally differ, UI labels say "Desktop" and "Runtime" explicitly.
- If the release is intended to be unified, the runtime image package version must be bumped to match the Desktop release.

## Proposed UX

### Start Screen

Show a compact runtime card:

- Status: Running, Starting, Needs attention, or Not started.
- URL: `http://127.0.0.1:<port>/ax-bi/welcome/`.
- Primary action: Open AX BI.
- Secondary actions: Restart runtime, View diagnostics, Settings.

### First-Run Setup

Show a setup screen before opening the login page:

1. "Create local admin account" or "Use generated local admin."
2. Confirm local-only runtime details.
3. Start runtime.
4. Open AX BI authenticated or show credentials with copy buttons.

### Diagnostics Panel

Show:

- Resolved binary paths and versions.
- Colima profile name, CPU, memory, and status.
- Docker context.
- Port bindings.
- Container health table.
- Last 100 runtime log lines per service.
- Copy diagnostics button.

## Metrics

Success metrics:

- 95% of fresh macOS local starts reach Running state without terminal intervention.
- 0 hidden-credential blockers in first-run user tests.
- Dashboard idle logging below 5 rows/minute.
- Uploaded file chart creation succeeds in first attempt for supported CSV/XLSX files.
- Support reports for "updated but still old version" reduce after version label clarification.

Guardrail metrics:

- No plaintext password leakage in logs.
- No regression in hosted/team login behavior.
- No loss of meaningful audit events for dashboard filter changes.

## Release Plan

### Phase 1: Runtime Reliability Hotfix

Scope:

- R1 dependency detection
- R2 health reconciliation
- R3 port detection
- R9 version labeling

Why first:

These issues make the product appear broken before users can evaluate AX BI.

### Phase 2: First-Run Onboarding

Scope:

- R5 credential/setup flow
- R6 webview session handling

Why second:

Once runtime status is reliable, users need a non-technical path into the app.

### Phase 3: Web Runtime Usability

Scope:

- R7 Explore sidebar data rendering
- R8 action-log noise reduction

Why third:

These issues affect core usage after login: upload, chart creation, dashboards, and observability.

## Open Questions

1. Should Desktop and web runtime versions always match, or are they separate products?
2. Should Desktop auto-login local admin by default, or should it always require an explicit local password?
3. What is the minimum supported Mac memory profile for AX BI local runtime?
4. Should Desktop own an isolated Colima profile such as `ax-bi`, or use the user's default Colima profile?
5. Should noisy action-log exclusions be configurable for enterprise audit requirements?

## Test Plan

### Manual QA Matrix

- Fresh macOS Apple Silicon machine with no Colima/Docker installed.
- Machine with Homebrew dependencies installed under `/opt/homebrew/bin`.
- Machine with port `8088` already occupied.
- Low-resource Colima profile.
- Existing healthy runtime after a transient compose failure.
- Desktop webview login and browser login against same runtime.
- Upload CSV/XLSX and create chart from Explore.
- Idle dashboard view for 10 minutes, then inspect Action Logs.

### Automated Coverage

- Unit tests for binary resolution and dependency detection.
- Unit tests for startup state transitions and stale-failure clearing.
- Integration test for compose health reconciliation.
- Webview cookie/session test for local auth.
- Frontend regression test for Explore metadata hydration after upload.
- Backend/frontend test for dashboard filter-state logging debounce or exclusion.

## Definition of Done

- All acceptance criteria for R1-R9 pass.
- Issues #1-#8 can be closed with linked PRs.
- Desktop diagnostics can explain the local runtime state without terminal commands.
- A first-time user can install, start, log in, upload data, create a chart, and view a dashboard without hidden setup steps.
