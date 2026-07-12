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
from collections.abc import Iterator

import pytest

from axbi.app import AxBIApp
from axbi.extensions import appbuilder
from axbi.initialization import AxBIAppInitializer


def _create_qa_app() -> AxBIApp:
    """Create a minimal AxBI app for standalone upload QA tests."""
    app = AxBIApp(__name__)
    app.config.from_object("axbi.config")
    app.config["SQLALCHEMY_DATABASE_URI"] = (
        os.environ.get("AXBI__SQLALCHEMY_DATABASE_URI") or "sqlite://"
    )
    app.config["WTF_CSRF_ENABLED"] = False
    app.config["PREVENT_UNSAFE_DB_CONNECTIONS"] = False
    app.config["TESTING"] = True
    app.config["RATELIMIT_ENABLED"] = False
    app.config["CACHE_CONFIG"] = {}
    app.config["DATA_CACHE_CONFIG"] = {}
    app.config["SERVER_NAME"] = "example.com"
    app.config["APPLICATION_ROOT"] = "/"
    app.config["PREFERRED_URL_SCHEME"] = "http"
    app.config["READ_CSV_CHUNK_SIZE"] = 1000

    appbuilder.baseviews = []
    AxBIAppInitializer(app).init_app()
    return app


QA_APP = _create_qa_app()


@pytest.fixture(scope="session")
def qa_app() -> AxBIApp:
    """Return the initialized QA AxBI app."""
    return QA_APP


@pytest.fixture(autouse=True)
def qa_app_context(qa_app: AxBIApp) -> Iterator[None]:
    """Provide Flask current_app config for upload readers used in QA."""
    with qa_app.app_context():
        yield
