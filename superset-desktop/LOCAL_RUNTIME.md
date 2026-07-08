# AX-BI Desktop Local Runtime

AX-BI Desktop should make local evaluation feel like a normal desktop
application while keeping AX-BI's server-backed architecture intact.

The target user path is:

```shell
brew install --cask defai-digital/ax-bi/ax-bi
```

After installation, the user opens AX-BI Desktop. The app offers two paths:

- Connect to an existing AX-BI server.
- Start AX-BI locally.

The local path is for trials, demos, and technical evaluators. Production users
should normally connect to a hosted or centrally managed AX-BI instance.

## Best-Practice Decision

Use Homebrew for installation, then let the Tauri app manage the local runtime.

Homebrew should install:

- AX-BI Desktop.
- Colima.
- Docker CLI.
- Docker Compose.

The Tauri app should manage:

- Local runtime configuration.
- Generated secrets.
- Compose file generation.
- Colima startup.
- AX-BI container lifecycle.
- Health checks, logs, updates, and reset flows.

Do not require users to clone this repository or edit `.env` files for a local
trial. Do not bundle Python, Superset, database drivers, Postgres, Redis, and
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

- `SUPERSET_SECRET_KEY`
- `DATABASE_PASSWORD`
- `ADMIN_PASSWORD`

The generated Compose stack uses published images:

- `ghcr.io/defai-digital/ax-bi:latest`
- `ghcr.io/defai-digital/ax-bi-services:latest`

Release builds should pin these tags to the AX-BI Desktop release train.

## Colima And Docker Isolation

The local runtime uses a dedicated Colima profile:

```text
ax-bi
```

Docker commands use the profile socket directly:

```text
DOCKER_HOST=unix://$HOME/.colima/ax-bi/docker.sock
```

This avoids changing the user's global Docker context and keeps AX-BI Desktop
from interfering with other Docker Desktop, Colima, or Podman workflows.

Public AX-BI services bind only to loopback:

```text
127.0.0.1:8088  AX-BI web app
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

The launcher UI and the AX-BI web app should not share the same privileged
webview.

Recommended window model:

- A local launcher window has access to local runtime commands.
- The AX-BI web app window loads `http://127.0.0.1:8088` or a configured
  hosted instance and has no local runtime privileges.

This keeps a server-side XSS or an untrusted AX-BI origin from gaining host
container-control capabilities.

## Release Plan

1. Build signed macOS `.app` artifacts from `superset-desktop/`.
2. Zip the `.app` bundle and publish it on a GitHub release.
3. Update the Homebrew cask in `defai-digital/homebrew-ax-bi`.
4. Users install or upgrade with:

   ```shell
   brew install --cask defai-digital/ax-bi/ax-bi
   brew upgrade --cask defai-digital/ax-bi/ax-bi
   ```

The cask template in `packaging/homebrew/Casks/ax-bi.rb.template` documents the
expected dependency and artifact shape.

Signed and notarized `.dmg` artifacts are still useful for direct downloads, but
the Homebrew path can install from a zipped `.app` bundle.
