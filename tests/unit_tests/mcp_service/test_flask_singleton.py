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

from __future__ import annotations

import os
import subprocess
import sys
import textwrap
from pathlib import Path


def test_flask_singleton_reuses_started_superset_app_without_context() -> None:
    """MCP helpers must not create or fail after Superset already started.

    Run in a subprocess so ``superset.mcp_service.flask_singleton`` is imported
    from a clean module state. This pins the real startup order: ``create_app()``
    initializes Flask-AppBuilder inside an app context, then MCP code later asks
    for the Flask app with no current context.
    """
    repo_root = Path(__file__).parents[3]
    env = {
        **os.environ,
        "AX_BI_SECRET_KEY": "test-secret-key-for-local-regression",
    }
    script = textwrap.dedent(
        """
        from superset.app import create_app

        created_app = create_app()

        from superset.mcp_service.flask_singleton import get_flask_app

        assert get_flask_app() is created_app
        """
    )

    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", script],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    assert result.returncode == 0, result.stderr
