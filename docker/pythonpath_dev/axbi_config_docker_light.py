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
#
# Configuration for docker-compose-light.yml - disables Redis and uses minimal services

# Import all settings from the main config first
import os

from flask_caching.backends.filesystemcache import FileSystemCache

from axbi_config import *  # noqa: F403

# Override caching to use simple in-memory cache instead of Redis
RESULTS_BACKEND = FileSystemCache(
    os.path.join(os.getenv("AXBI_HOME", "/app/axbi_home"), "sqllab")
)

CACHE_CONFIG = {
    "CACHE_TYPE": "SimpleCache",
    "CACHE_DEFAULT_TIMEOUT": 300,
    "CACHE_KEY_PREFIX": "axbi_light_",
}
DATA_CACHE_CONFIG = CACHE_CONFIG
THUMBNAIL_CACHE_CONFIG = CACHE_CONFIG


# Disable Celery entirely for lightweight mode
CELERY_CONFIG = None  # type: ignore[assignment,misc]

# Honor AXBI_FEATURE_<NAME> env vars on top of any flags inherited from
# axbi_config. Lets local dev/e2e enable features (e.g. EMBEDDED_AXBI)
# without editing shipped config files. Only the literal string "true"
# (case-insensitive) is treated as enabled — "1"/"yes"/"on" are not, matching
# the strict-string convention used elsewhere in AxBI's env parsing.
FEATURE_FLAGS = {
    **FEATURE_FLAGS,  # noqa: F405
    **{
        name[len("AXBI_FEATURE_") :]: value.strip().lower() == "true"
        for name, value in os.environ.items()
        if name.startswith("AXBI_FEATURE_")
    },
}

if os.environ.get("AXBI_FEATURE_EMBEDDED_AXBI", "").strip().lower() == "true":
    # Disable Talisman so /embedded/<uuid> doesn't return X-Frame-Options:SAMEORIGIN.
    # Without this, browsers refuse to render AxBI inside an iframe from a
    # different origin (i.e. the embedded SDK use case). Production/CI configures
    # Talisman with explicit `frame-ancestors`; for the lightweight local stack we
    # just turn it off.
    TALISMAN_ENABLED = False

    # Guest tokens (used by the embedded SDK) inherit the "Public" role's perms.
    # Out of the box Public has zero perms, so embedded dashboards immediately fail
    # their first call (`/api/v1/me/roles/`) with 403. Mirror Public to Gamma —
    # the standard read-only viewer role — so the embedded flow can authenticate
    # and load dashboard data in local dev.
    PUBLIC_ROLE_LIKE = "Gamma"
