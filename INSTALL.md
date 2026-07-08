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

# Installing AX BI

AX BI is a Superset-based BI application with an MCP service for AI-assisted
analytics workflows. The recommended install path is Docker Compose. Local
source runs are useful for development and Ax Studio MCP testing.

## Docker Quick Start

Install Docker, Docker Compose, Git, and `openssl`, then run:

```shell
git clone https://github.com/defai-digital/ax-bi.git
cd ax-bi
cp docker/.env-axbi.example docker/.env-axbi
```

Edit `docker/.env-axbi` and set:

```env
AX_BI_SECRET_KEY=<generated secret>
DATABASE_PASSWORD=<generated database password>
ADMIN_PASSWORD=<admin login password>
MCP_DEV_USERNAME=admin
```

Generate secrets with:

```shell
openssl rand -base64 42
```

Start AX BI:

```shell
docker compose --env-file docker/.env-axbi -f docker-compose-axbi.yml up -d
```

Open:

| Service | URL |
| --- | --- |
| AX BI web app | `http://localhost:8088/ax-bi/welcome/` |
| AX BI MCP service | `http://localhost:5008/mcp` |
| AX services sidecar | `http://localhost:5010` |

Log in with:

```text
username: admin
password: ADMIN_PASSWORD from docker/.env-axbi
```

For shared or production deployments, leave `MCP_DEV_USERNAME` empty and
configure JWT authentication for MCP before exposing it outside localhost.

## Local Source Run

From a prepared checkout with dependencies installed:

```shell
cd /path/to/ax-bi
source venv/bin/activate
FLASK_DEBUG=1 SUPERSET_ENV=development \
  venv/bin/superset run -h 127.0.0.1 -p 8080 --with-threads --no-reload
```

In a second terminal, start MCP for local Ax Studio testing:

```shell
cd /path/to/ax-bi
source venv/bin/activate
MCP_DEV_USERNAME=admin \
SUPERSET_WEBSERVER_ADDRESS=http://127.0.0.1:8080 \
WEBDRIVER_BASEURL=http://127.0.0.1:8080/ \
WEBDRIVER_BASEURL_USER_FRIENDLY=http://127.0.0.1:8080/ \
  venv/bin/superset mcp run --host 127.0.0.1 --port 5008 --debug
```

Open the web app at:

```text
http://127.0.0.1:8080/ax-bi/welcome/
```

Connect Ax Studio to:

```text
http://127.0.0.1:5008/mcp
```

## Notes

- The technical route prefix remains `/ax-bi`.
- Legacy `/superset` links redirect to `/ax-bi` for compatibility with
  upstream Superset routes.
- MCP chart and dashboard URLs should use `127.0.0.1` or your real host, not
  `0.0.0.0`, because `0.0.0.0` is only a bind address.
- The underlying Superset documentation remains useful for advanced database,
  Helm, and production architecture topics:
  [Superset installation docs](https://superset.apache.org/docs/installation/installation-methods).
