# AX BI default ports

Application services use a contiguous block starting at **31421**.
Infrastructure defaults (Postgres, Redis) stay on their standard ports.

| Port | Service | Default URL / path |
|-----:|---------|--------------------|
| **31421** | MCP | `http://127.0.0.1:31421/mcp` |
| **31422** | Frontend (webpack dev) | `http://127.0.0.1:31422` |
| **31423** | Web app (Flask) | `http://127.0.0.1:31423/ax-bi/welcome/` |
| **31424** | AX Services sidecar | `http://127.0.0.1:31424` (`/health`, `/ready`) |
| **31425** | Async queries WebSocket | `ws://127.0.0.1:31425/` |
| **31426** | WebSocket HTTP helper / Cypress helper | (compose) |
| **31427** | Storybook | `http://127.0.0.1:31427` |
| **31428** | Celery Flower (optional) | Helm / Flower UI |

## Infrastructure (unchanged)

| Port | Service |
|-----:|---------|
| 5432 | PostgreSQL |
| 6379 | Redis |

## Common web paths (web app :31423)

| Path | Purpose |
|------|---------|
| `/health` | Health check |
| `/login/` | Login |
| `/ax-bi/welcome/` | Home after login |
| `/api/v1/...` | REST API |
| `/static/assets/...` | Frontend assets |

## Environment overrides

| Variable | Default | Service |
|----------|--------:|---------|
| `MCP_PORT` | 31421 | MCP |
| `NODE_PORT` / `WEBPACK_DEVSERVER_PORT` | 31422 | Frontend dev |
| `AXBI_PORT` | 31423 | Web app |
| `AX_SERVICES_PORT` | 31424 | AX Services |
| `WEBSOCKET_PORT` | 31425 | Async WS |
| `WEBSOCKET_HTTP_PORT` | 31426 | WS HTTP |
| `DATABASE_PORT` | 5432 | Postgres |
| `REDIS_PORT` | 6379 | Redis |

## Backup

There is no dedicated backup network port. Back up Postgres (5432) / volumes
and use CLI export commands for assets.

## Previous defaults (for migration)

| Service | Old | New |
|---------|----:|----:|
| MCP | 5008 | 31421 |
| Frontend | 9000 | 31422 |
| Web app | 8088 | 31423 |
| AX Services | 5010 | 31424 |
| WebSocket | 8080 | 31425 |
| WS HTTP | 8081 | 31426 |
| Storybook | 6006 | 31427 |
| Flower | 5555 | 31428 |
