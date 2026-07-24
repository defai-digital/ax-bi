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

AX BI is an independently maintained BI application with an MCP service for
AI-assisted analytics workflows. The recommended install path is Docker
Compose. Local source runs are useful for development and AX Studio MCP testing.

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
| AX BI web app | `http://localhost:31423/ax-bi/welcome/` |
| AX BI MCP service | `http://localhost:31421/mcp` |
| AX services sidecar | `http://localhost:31424` |

Log in with:

```text
username: admin
password: ADMIN_PASSWORD from docker/.env-axbi
```

For shared or production deployments, leave `MCP_DEV_USERNAME` empty and
configure JWT authentication for MCP before exposing it outside localhost.

## Local Source Run

Use a single project virtualenv at `./venv` on **Python 3.12+** (not a stray
`.venv` and not a 3.11 tree). The editor does **not** auto-activate it; load
it only when you need project tools:

```shell
make venv              # create if missing; fail if wrong Python version
# make venv-recreate   # if an old 3.11 venv is present
source venv/bin/activate
# or without activating: ./venv/bin/python, ./venv/bin/ax-bi, ./venv/bin/pytest
```

From a prepared checkout with dependencies installed:

```shell
cd /path/to/ax-bi
source venv/bin/activate
FLASK_DEBUG=1 AXBI_ENV=development \
  venv/bin/ax-bi run -h 127.0.0.1 -p 8080 --with-threads --no-reload
```

In a second terminal, start MCP for local AX Studio testing:

```shell
cd /path/to/ax-bi
source venv/bin/activate
MCP_DEV_USERNAME=admin \
AXBI_WEBSERVER_ADDRESS=http://127.0.0.1:8080 \
WEBDRIVER_BASEURL=http://127.0.0.1:8080/ \
WEBDRIVER_BASEURL_USER_FRIENDLY=http://127.0.0.1:8080/ \
  venv/bin/ax-bi mcp run --host 127.0.0.1 --port 31421 --debug
```

Open the web app at:

```text
http://127.0.0.1:8080/ax-bi/welcome/
```

Connect AX Studio to:

```text
http://127.0.0.1:31421/mcp
```

Use that same MCP URL for LM Studio. Do not enter the AX BI welcome URL: it is
an HTML web page, not an MCP endpoint. Generate and copy the MCP key from this
same AX BI deployment; keys from a different installation or keys replaced
from another browser tab are invalid.

## Notes

- The application route prefix is `/ax-bi`; no former-name redirect is
  registered.
- MCP chart and dashboard URLs should use `127.0.0.1` or your real host, not
  `0.0.0.0`, because `0.0.0.0` is only a bind address.
- The upstream documentation remains useful as historical background for some
  database connectors:
  [Superset installation docs](https://superset.apache.org/docs/installation/installation-methods).
