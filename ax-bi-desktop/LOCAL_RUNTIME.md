# AX BI Desktop Local Runtime

AX BI Desktop should make local evaluation feel like a normal desktop
application while keeping AX BI's server-backed architecture intact.

The target user path is the Homebrew tap
[defai-digital/homebrew-ax-bi](https://github.com/defai-digital/homebrew-ax-bi):

```shell
brew install --cask defai-digital/ax-bi/ax-bi
```

Or explicitly:

```shell
brew tap defai-digital/ax-bi https://github.com/defai-digital/homebrew-ax-bi
brew install --cask ax-bi
```

After installation, the user opens AX BI Desktop. The bundled launcher offers
two first-class paths:

- **Run locally** — start the **same** AX BI Docker Compose stack on **macOS or
  Windows** (engine differs; images/ports do not).
- Connect to an existing hosted or team-managed AX BI server.

Local is a supported day-to-day option for individuals and small teams, not only
a short-lived trial. Hosted/centralized deployments remain the better fit for
shared multi-user production environments.

## Best-Practice Decision

Use Homebrew for installation, then let the Tauri app manage the local runtime.

**macOS (Homebrew)** should install:

- AX BI Desktop.
- Colima.
- Lima (`limactl`, required by Colima).
- Docker CLI.
- Docker Compose.

**Windows** expects:

- AX BI Desktop (Authenticode-signed NSIS/MSI from GitHub Releases, or
  `winget install -e --id DEFAI.AXBI` once published — see
  [`packaging/winget/`](packaging/winget/README.md)).
- Docker Desktop (or any Docker Engine the CLI can reach). Prefer
  `winget install -e --id Docker.DockerDesktop` on modern Windows.

The Tauri app should manage:

- Local runtime configuration.
- Generated secrets.
- Compose file generation.
- Platform engine startup (Colima on macOS; Docker Desktop/engine on Windows).
- AX BI container lifecycle.
- Health checks, logs, updates, and reset flows.

Do not require users to clone this repository or edit `.env` files for a local
instance. Do not bundle Python, Superset, database drivers, Postgres, Redis, and
their migrations directly inside the desktop app unless offline local BI becomes
a separate product requirement.

## Runtime Ownership

The native runtime manager writes files under the Tauri app data directory:

```text
<app-data-dir>/local-runtime/
├── .admin-onboarding-complete
├── .env
└── docker-compose.yml
```

The generated `.env` contains local-only secrets:

- `AX_BI_SECRET_KEY` (random)
- `AX_SERVICES_INTERNAL_TOKEN` (random, shared only by AX BI and AX Services)
- `DATABASE_PASSWORD` (random)
- `ADMIN_PASSWORD` (random, generated when the runtime is first prepared)
- `COLIMA_PROFILE` (`ax-bi` for new installs; an existing managed `default`
  profile is adopted during upgrade)

Desktop displays the local admin username and generated password before opening
AX BI for the first time. The credentials remain available from **Settings >
Advanced runtime > Credentials**. Updates preserve existing `.env` credentials.
Desktop automatically adds newly required generated secrets to an existing
runtime without rotating valid values. On Unix, `.env` permissions are kept at
`0600` because the file contains local credentials.

The generated Compose stack uses published images:

- `ghcr.io/defai-digital/ax-bi:latest`
- `ghcr.io/defai-digital/ax-bi-services:latest`

Release builds should pin these tags to the AX BI Desktop release train.

## Platform Engines

**Yes — both macOS and Windows run local AX BI via Docker.** Compose YAML, image
tags, and loopback ports are identical. Only the container engine adapter differs.

On macOS, Desktop validates the selected Colima profile before startup. Profiles
below 4 CPUs or 8 GiB memory are restarted with the recommended resources.
When the managed Docker endpoint is already responsive, Desktop reads those
values from Colima's generated profile rather than blocking on its slower status
command.

### macOS — Colima (isolated)

Uses a dedicated Colima profile:

```text
ax-bi
```

Docker commands use the profile socket directly:

```text
DOCKER_HOST=unix://$HOME/.colima/ax-bi/docker.sock
```

This avoids changing the user's global Docker context and keeps AX BI Desktop
from interfering with other Docker Desktop, Colima, or Podman workflows.

GUI-launched apps (Finder / Dock) do not inherit a login-shell `PATH`. The
native runtime always injects Homebrew prefixes (`/opt/homebrew/bin`,
`/usr/local/bin`) so Colima can find `limactl` and the Docker CLI. Missing
Lima produces a clear install hint (`brew install lima colima`).

### Windows — Docker Engine

Uses the host Docker Engine default endpoint (Docker Desktop named pipe when
Desktop is installed). The app does **not** set a custom `DOCKER_HOST`.

On **Start**, if the Docker CLI is present but the engine is down, the app
attempts to launch Docker Desktop and waits until `docker info` succeeds.

Install Docker Desktop from Microsoft/Docker docs if dependencies are missing.

### Shared service binds

Public AX BI services bind only to loopback on every platform:

```text
127.0.0.1:31423  AX BI web app
127.0.0.1:31421  MCP service
127.0.0.1:31424  AX Services
```

The host-side values can be changed in the generated `.env`; the web container
listener remains on internal port `31423` so its mapping and health check cannot
drift apart.

## Native Commands

The Tauri native layer exposes typed commands for the launcher UI:

- `get_local_runtime_status`
- `prepare_local_runtime`
- `start_local_runtime`
- `stop_local_runtime`
- `restart_local_runtime`
- `update_local_runtime`
- `get_local_runtime_logs`
- `get_local_admin_credentials`

Status includes `engine_name`, `engine_label`, `engine_running`, and
`stack_running` (plus legacy `colima_*` fields for older clients). A partial
stack remains stoppable and is shown as needing attention instead of stopped.
Commands call fixed engine + Docker Compose flows. They do not expose an
arbitrary shell command bridge to web content.

## Launcher UI Boundary

The local runtime commands are guarded so they only run from the bundled Tauri
launcher origin.

Recommended window model:

- A local launcher window has access to local runtime commands.
- The AX BI web app window loads `http://127.0.0.1:31423` or a configured
  hosted instance and has no local runtime privileges.

An already healthy managed runtime opens automatically at Desktop startup. The
AX BI web app window is explicitly shown and focused before the launcher hides,
so the startup handoff cannot leave both windows in the background.

This keeps a server-side XSS or an untrusted AX BI origin from gaining host
container-control capabilities.

## Release Plan

Automated by [`.github/workflows/ax-bi-desktop-release.yml`](../.github/workflows/ax-bi-desktop-release.yml).
See [RELEASE.md](RELEASE.md) for secrets, minisign, and maintainer steps.

1. Tag `ax-bi-desktop-vX.Y.Z` (or run the workflow with a version input).
2. Build **signed + notarized** macOS arm64 DMG (`AX BI.app` product name).
3. Build Windows installers (product name **AX BI**).
4. minisign all GitHub Release assets.
5. Publish the release, then push `Casks/ax-bi.rb` to
   [defai-digital/homebrew-ax-bi](https://github.com/defai-digital/homebrew-ax-bi)
   (DMG URL + SHA256; Colima/Docker formulas as `depends_on`).

Users install or upgrade with:

```shell
brew install --cask defai-digital/ax-bi/ax-bi
brew upgrade --cask defai-digital/ax-bi/ax-bi
```

The cask installs **AX BI.app**. Local runtime (Colima + Lima + Compose) is
managed by the app after install. On Windows, install Docker Desktop once
(`winget install -e --id Docker.DockerDesktop` or Docker’s installer); the app
manages Compose lifecycle against that engine.
