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
"""Docker deployment configuration for AX BI."""

from __future__ import annotations

import logging
import os

from celery.schedules import crontab
from flask_caching.backends.filesystemcache import FileSystemCache


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} must be set for AX BI Docker deployment")
    return value


def _bool_env(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DATABASE_DIALECT = os.getenv("DATABASE_DIALECT", "postgresql")
DATABASE_USER = os.getenv("DATABASE_USER", "axbi")
DATABASE_PASSWORD = _required_env("DATABASE_PASSWORD")
DATABASE_HOST = os.getenv("DATABASE_HOST", "db")
DATABASE_PORT = os.getenv("DATABASE_PORT", "5432")
DATABASE_DB = os.getenv("DATABASE_DB", "axbi")

SECRET_KEY = _required_env("AX_BI_SECRET_KEY")

SQLALCHEMY_DATABASE_URI = (
    f"{DATABASE_DIALECT}://"
    f"{DATABASE_USER}:{DATABASE_PASSWORD}@"
    f"{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_DB}"
)

AXBI_HOME = os.getenv("AXBI_HOME", "/app/axbi_home")
UPLOAD_FOLDER = os.getenv(
    "UPLOAD_FOLDER",
    os.path.join(AXBI_HOME, "uploads"),
)
LOCAL_DB_NAME = os.getenv("LOCAL_DB_NAME", "Local Files")
LOCAL_DB_PATH = os.getenv(
    "LOCAL_DB_PATH",
    os.path.join(UPLOAD_FOLDER, "local_files.duckdb"),
)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = os.getenv("REDIS_PORT", "6379")
REDIS_CELERY_DB = os.getenv("REDIS_CELERY_DB", "0")
REDIS_RESULTS_DB = os.getenv("REDIS_RESULTS_DB", "1")

RESULTS_BACKEND = FileSystemCache(os.path.join(AXBI_HOME, "sqllab"))

CACHE_CONFIG = {
    "CACHE_TYPE": "RedisCache",
    "CACHE_DEFAULT_TIMEOUT": int(os.getenv("CACHE_DEFAULT_TIMEOUT", "300")),
    "CACHE_KEY_PREFIX": os.getenv("CACHE_KEY_PREFIX", "axbi_"),
    "CACHE_REDIS_HOST": REDIS_HOST,
    "CACHE_REDIS_PORT": REDIS_PORT,
    "CACHE_REDIS_DB": REDIS_RESULTS_DB,
}
DATA_CACHE_CONFIG = CACHE_CONFIG
THUMBNAIL_CACHE_CONFIG = CACHE_CONFIG


class CeleryConfig:
    """Celery settings for the AX BI Docker stack."""

    broker_url = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_CELERY_DB}"
    result_backend = f"redis://{REDIS_HOST}:{REDIS_PORT}/{REDIS_RESULTS_DB}"
    imports = (
        "axbi.sql_lab",
        "axbi.tasks.scheduler",
        "axbi.tasks.thumbnails",
        "axbi.tasks.cache",
    )
    worker_prefetch_multiplier = 1
    task_acks_late = False
    beat_schedule = {
        "reports.scheduler": {
            "task": "reports.scheduler",
            "schedule": crontab(minute="*", hour="*"),
        },
        "reports.prune_log": {
            "task": "reports.prune_log",
            "schedule": crontab(minute=10, hour=0),
        },
    }


CELERY_CONFIG = CeleryConfig

FEATURE_FLAGS = {
    "ALERT_REPORTS": True,
    "DATASET_FOLDERS": True,
    "ENABLE_EXTENSIONS": True,
    # GenAI BI profile: expose MCP intent tools (prompt-to-dashboard, etc.).
    # GENAI_BI alone is not enough — AI tools also require GENAI_BI_MCP_TOOLS
    # (and GENAI_PROMPT_TO_DASHBOARD for plan/compose/orchestrator tools).
    "GENAI_BI": _bool_env("GENAI_BI", True),
    "GENAI_BI_MCP_TOOLS": _bool_env("GENAI_BI_MCP_TOOLS", True),
    "GENAI_PROMPT_TO_DASHBOARD": _bool_env("GENAI_PROMPT_TO_DASHBOARD", True),
    "GENAI_EMBEDDED_ASSISTANT": _bool_env("GENAI_EMBEDDED_ASSISTANT", False),
    "GENAI_SEMANTIC_INDEX": _bool_env("GENAI_SEMANTIC_INDEX", False),
    "GENAI_SEMANTIC_INDEX_PGVECTOR": _bool_env(
        "GENAI_SEMANTIC_INDEX_PGVECTOR",
        False,
    ),
    "SEMANTIC_LAYERS": True,
}

# Optional server-side LLM for intent mapping / dashboard planning (Admin/operator).
# When empty, tools fall back to keyword heuristics or LLM_NOT_CONFIGURED.
# Do not pass inference URLs from AX Studio end users — only env/Admin config.
from axbi.genai.llm_config import build_provider_config_from_env

GENAI_LLM_PROVIDER_CONFIG: dict = build_provider_config_from_env()

# Optional: allow bounded sample values in GenAI prompts (default off).
GENAI_LLM_ALLOW_BOUNDED_SAMPLES = _bool_env("GENAI_LLM_ALLOW_BOUNDED_SAMPLES", False)
GENAI_LLM_BOUNDED_SAMPLE_MAX_ROWS = int(
    os.getenv("GENAI_LLM_BOUNDED_SAMPLE_MAX_ROWS", "5")
)
GENAI_LLM_BOUNDED_SAMPLE_MAX_COLUMNS = int(
    os.getenv("GENAI_LLM_BOUNDED_SAMPLE_MAX_COLUMNS", "10")
)

AI_SEMANTIC_EMBEDDING_PROVIDER = os.getenv(
    "AI_SEMANTIC_EMBEDDING_PROVIDER",
    "ax_engine_http",
)
AI_SEMANTIC_EMBEDDING_ENDPOINT = os.getenv(
    "AI_SEMANTIC_EMBEDDING_ENDPOINT",
    "http://host.docker.internal:8099/embed",
)
AI_SEMANTIC_EMBEDDING_MODEL = os.getenv(
    "AI_SEMANTIC_EMBEDDING_MODEL",
    "Qwen/Qwen3-Embedding-0.6B",
)
AI_SEMANTIC_EMBEDDING_DIMENSIONS = int(
    os.getenv("AI_SEMANTIC_EMBEDDING_DIMENSIONS", "1024")
)
AI_SEMANTIC_EMBEDDING_TIMEOUT = int(os.getenv("AI_SEMANTIC_EMBEDDING_TIMEOUT", "120"))
AI_SEMANTIC_INDEX_TOP_K = int(os.getenv("AI_SEMANTIC_INDEX_TOP_K", "10"))
AI_SEMANTIC_INDEX_HNSW_EF_SEARCH = int(
    os.getenv("AI_SEMANTIC_INDEX_HNSW_EF_SEARCH", "100")
)

ENABLE_PROXY_FIX = _bool_env("ENABLE_PROXY_FIX", True)
TALISMAN_ENABLED = _bool_env("TALISMAN_ENABLED", True)
SQLLAB_CTAS_NO_LIMIT = _bool_env("SQLLAB_CTAS_NO_LIMIT", True)

WEBDRIVER_BASEURL = os.getenv("WEBDRIVER_BASEURL", "http://ax-bi:8088/")
WEBDRIVER_BASEURL_USER_FRIENDLY = os.getenv(
    "WEBDRIVER_BASEURL_USER_FRIENDLY",
    "http://localhost:8088/",
)

MCP_AUTH_ENABLED = _bool_env("MCP_AUTH_ENABLED", False)
MCP_DEV_USERNAME = os.getenv("MCP_DEV_USERNAME") or None
MCP_JWT_ISSUER = os.getenv("MCP_JWT_ISSUER") or None
MCP_JWT_AUDIENCE = os.getenv("MCP_JWT_AUDIENCE") or None
MCP_JWT_ALGORITHM = os.getenv("MCP_JWT_ALGORITHM", "RS256")
MCP_JWKS_URI = os.getenv("MCP_JWKS_URI") or None
MCP_JWT_PUBLIC_KEY = os.getenv("MCP_JWT_PUBLIC_KEY") or None
MCP_JWT_SECRET = os.getenv("MCP_JWT_SECRET") or None
MCP_REQUIRED_SCOPES = [
    scope.strip()
    for scope in os.getenv("MCP_REQUIRED_SCOPES", "").split(",")
    if scope.strip()
]

LOG_LEVEL = getattr(
    logging,
    os.getenv("AXBI_LOG_LEVEL", "INFO").upper(),
    logging.INFO,
)
