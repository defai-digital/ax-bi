# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


def test_docker_web_port_defaults_use_the_canonical_port() -> None:
    """Keep image, entrypoint, health, and Compose defaults on port 31423."""
    expected_snippets = {
        "Dockerfile": 'AXBI_PORT="31423"',
        "docker/.env": "AXBI_PORT=31423",
        "docker/docker-bootstrap.sh": "PORT=${PORT:-31423}",
        "docker/docker-healthcheck.sh": "${AXBI_PORT:-31423}",
        "docker/entrypoints/run-server.sh": "${AXBI_PORT:-31423}",
        "docker-compose-axbi.yml": "AXBI_PORT: 31423",
        "scripts/docker-compose-up.sh": "get_running_port ax-bi 31423",
    }

    for relative_path, expected in expected_snippets.items():
        content = (REPOSITORY_ROOT / relative_path).read_text()
        assert expected in content, f"{relative_path} is missing {expected!r}"
