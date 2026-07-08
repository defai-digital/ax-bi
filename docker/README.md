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

# Getting Started with AX BI Using Docker

Docker is the recommended way to deploy AX BI for users who want a
self-contained stack. The AX BI stack includes Superset, the MCP service, the
TypeScript `ax-services` sidecar, Postgres, Redis, Celery worker, and Celery
beat.

## Prerequisites

1. [Docker](https://www.docker.com/get-started)
2. [Docker Compose](https://docs.docker.com/compose/install/)
3. `openssl` for generating local secrets

## Quick Start

Clone the repository and run these commands from the repository root:

```shell
git clone https://github.com/defai-digital/ax-bi.git
cd ax-bi
```

```shell
cp docker/.env-axbi.example docker/.env-axbi
```

Edit `docker/.env-axbi` and fill:

```env
SUPERSET_SECRET_KEY=<generated secret>
DATABASE_PASSWORD=<generated database password>
ADMIN_PASSWORD=<admin login password>
```

Generate each secret value with:

```shell
openssl rand -base64 42
```

Then start AX BI:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
```

This pulls the public images:

```text
ghcr.io/defai-digital/ax-bi:latest
ghcr.io/defai-digital/ax-bi-services:latest
```

The first startup initializes the metadata database, applies migrations, creates
the admin user, and starts the web app, MCP service, sidecar, Redis, and Celery.

Check status:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml ps
```

Services are exposed locally on:

| Service | Default URL |
|---------|-------------|
| AX BI web app | `http://localhost:8088/ax-bi/welcome/` |
| MCP service | `http://localhost:5008/mcp` |
| AX services sidecar | `http://localhost:5010` |

Log in to the web app with:

```text
username: admin
password: ADMIN_PASSWORD from docker/.env-axbi
```

## Common Operations

View logs:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml logs -f
```

Stop without deleting data:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml stop
```

Pull newer images and restart:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml pull
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
```

Remove containers and volumes:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml down -v
```

## Build from Source

The quick start pulls published images. To build from this checkout instead,
run:

```shell
docker compose \
  --env-file docker/.env-axbi \
  -f docker-compose-axbi.yml \
  -f docker-compose-axbi-build.yml \
  up -d --build
```

## Shared or Public Deployments

For a local single-user trial, you may set `MCP_DEV_USERNAME=admin` in
`docker/.env-axbi`. For production or any shared deployment:

- Leave `MCP_DEV_USERNAME` empty.
- Configure JWT settings for the MCP service: `MCP_AUTH_ENABLED`,
  `MCP_JWT_ISSUER`, `MCP_JWT_AUDIENCE`, `MCP_JWKS_URI`, and optional
  `MCP_REQUIRED_SCOPES`.
- Put the AX BI web app behind HTTPS.
- Keep Postgres and Redis private.
- Pin image tags instead of using `latest`.
- Back up the Postgres metadata database.

### Configuration

The AX BI Docker image includes
[`./docker/pythonpath_axbi/superset_config.py`](./pythonpath_axbi/superset_config.py),
an environment-driven configuration for Docker deployments.

### Local Development Stack

The default [`../docker-compose.yml`](../docker-compose.yml) remains a
development stack with bind mounts, hot reload, frontend dev server, and
development defaults.

The `/app/pythonpath` folder is mounted from
[`./docker/pythonpath_dev`](./pythonpath_dev), which contains a base
configuration intended for local development.

#### Local overrides

##### Environment Variables

To override environment variables locally, create a `./docker/.env-local` file (git-ignored). This file will be loaded after `.env` and can override any settings.

##### Python Configuration

In order to override configuration settings locally, simply make a copy of [`./docker/pythonpath_dev/superset_config_local.example`](./pythonpath_dev/superset_config_local.example)
into `./docker/pythonpath_dev/superset_config_docker.py` (git-ignored) and fill in your overrides.

##### WebSocket Configuration

To customize the WebSocket server configuration, create `./docker/superset-websocket/config.json` (git-ignored) based on [`./docker/superset-websocket/config.example.json`](./superset-websocket/config.example.json).

Then update the `superset-websocket`.`volumes` config to mount it.

##### Docker Compose Overrides

For advanced Docker Compose customization, create a `docker-compose-override.yml` file (git-ignored) to override or extend services without modifying the main compose file.

#### Local packages

If you want to add Python packages in order to test things like databases locally, you can simply add a local requirements.txt (`./docker/requirements-local.txt`)
and rebuild your Docker stack.

Steps:

1. Create `./docker/requirements-local.txt`
2. Add your new packages
3. Rebuild docker compose
    1. `docker compose down -v`
    2. `docker compose up`

## Initializing Database

The database will initialize itself upon startup via the init container ([`superset-init`](./docker-init.sh)). This may take a minute.

## Development Operation

To run the development containers, run: `docker compose up`

After waiting several minutes for Superset initialization to finish, you can open a browser and view [`http://localhost:8088/ax-bi/welcome/`](http://localhost:8088/ax-bi/welcome/)
to start your journey.

### Running Multiple Instances

If you need to run multiple Superset instances simultaneously (e.g., different branches or clones), use the make targets which automatically find available ports:

```bash
make up
```

This automatically:
- Generates a unique project name from your directory
- Finds available ports (incrementing from defaults if in use)
- Displays the assigned URLs before starting

Available commands (run from repo root):

| Command | Description |
|---------|-------------|
| `make up` | Start services (foreground) |
| `make up-detached` | Start services (background) |
| `make down` | Stop all services |
| `make ps` | Show running containers |
| `make logs` | Follow container logs |
| `make nuke` | Stop, remove volumes & local images |

From a subdirectory, use: `make -C $(git rev-parse --show-toplevel) up`

**Important**: Always use these commands instead of plain `docker compose down`, which won't know the correct project name.

## Developing

While running, the container server will reload on modification of the Superset Python and JavaScript source code.
Don't forget to reload the page to take the new frontend into account though.

## Resource Constraints

If you are attempting to build on macOS and it exits with 137 you need to increase your Docker resources. See instructions [here](https://docs.docker.com/docker-for-mac/#advanced) (search for memory)
