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

- Run AX BI locally (app-managed Colima + Docker Compose).
- Connect to an existing hosted or team-managed AX BI server.

Local is a supported day-to-day option for individuals and small teams, not only
a short-lived trial. Hosted/centralized deployments remain the better fit for
shared multi-user production environments.

## Best-Practice Decision

Use Homebrew for installation, then let the Tauri app manage the local runtime.

Homebrew should install:

- AX BI Desktop.
- Colima.
- Docker CLI.
- Docker Compose.

The Tauri app should manage:

- Local runtime configuration.
- Generated secrets.
- Compose file generation.
- Colima startup.
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
├── .env
└── docker-compose.yml
```

The generated `.env` contains local-only secrets:

- `AX_BI_SECRET_KEY` (random)
- `DATABASE_PASSWORD` (random)
- `ADMIN_PASSWORD` (default `admin` — local desktop default login is `admin` / `admin`)

The generated Compose stack uses published images:

- `ghcr.io/defai-digital/ax-bi:latest`
- `ghcr.io/defai-digital/ax-bi-services:latest`

Release builds should pin these tags to the AX BI Desktop release train.

## Colima And Docker Isolation

The local runtime uses a dedicated Colima profile:

```text
ax-bi
```

Docker commands use the profile socket directly:

```text
DOCKER_HOST=unix://$HOME/.colima/ax-bi/docker.sock
```

This avoids changing the user's global Docker context and keeps AX BI Desktop
from interfering with other Docker Desktop, Colima, or Podman workflows.

Public AX BI services bind only to loopback:

```text
127.0.0.1:8088  AX BI web app
127.0.0.1:5008  MCP service
127.0.0.1:5010  AX Services
```

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

These commands call fixed Colima and Docker Compose flows. They do not expose an
arbitrary shell command bridge to web content.

## Launcher UI Boundary

The local runtime commands are guarded so they only run from the bundled Tauri
launcher origin.

Recommended window model:

- A local launcher window has access to local runtime commands.
- The AX BI web app window loads `http://127.0.0.1:8088` or a configured
  hosted instance and has no local runtime privileges.

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

The cask installs **AX BI.app**. Local runtime (Colima + Compose) is managed by
the app after install.
