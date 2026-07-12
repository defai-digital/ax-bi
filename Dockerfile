#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

######################################################################
# Node stage to deal with static asset construction
######################################################################
ARG PY_VER=3.12.12-slim-trixie

# If BUILDPLATFORM is null, set it to 'amd64' (or leave as is otherwise).
ARG BUILDPLATFORM=${BUILDPLATFORM:-amd64}

# Include translations in the final build
ARG BUILD_TRANSLATIONS="false"

######################################################################
# axbi-node-ci used as a base for building frontend assets and CI
######################################################################
FROM --platform=${BUILDPLATFORM} node:24-trixie-slim AS axbi-node-ci
ARG BUILD_TRANSLATIONS
ENV BUILD_TRANSLATIONS=${BUILD_TRANSLATIONS}
ARG DEV_MODE="false"           # Skip frontend build in dev mode
ENV DEV_MODE=${DEV_MODE}

COPY docker/ /app/docker/
# Arguments for build configuration
ARG NPM_BUILD_CMD="build"

# Install system dependencies required for node-gyp
RUN /app/docker/apt-install.sh build-essential python3 zstd

# Define environment variables for frontend build
ENV BUILD_CMD=${NPM_BUILD_CMD} \
    PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true

# Run the frontend memory monitoring script
RUN /app/docker/frontend-mem-nag.sh

WORKDIR /app/ax-bi-frontend

# Create necessary folders to avoid errors in subsequent steps
RUN mkdir -p /app/axbi/static/assets \
             /app/axbi/translations

# Harden `npm ci` against transient npm-registry network blips (e.g. ECONNRESET),
# which otherwise fail the entire multi-platform image build with no retry.
ENV npm_config_fetch_retries=5 \
    npm_config_fetch_retry_mintimeout=20000 \
    npm_config_fetch_retry_maxtimeout=120000 \
    npm_config_fetch_timeout=600000

# Mount package files and install dependencies if not in dev mode
# NOTE: we mount packages and plugins as they are referenced in package.json as workspaces
# ideally we'd COPY only their package.json. Here npm ci will be cached as long
# as the full content of these folders don't change, yielding a decent cache reuse rate.
# Note that it's not possible to selectively COPY or mount using blobs.
RUN --mount=type=bind,source=./ax-bi-frontend/package.json,target=./package.json \
    --mount=type=bind,source=./ax-bi-frontend/package-lock.json,target=./package-lock.json \
    --mount=type=cache,target=/root/.cache \
    --mount=type=cache,target=/root/.npm \
    if [ "${DEV_MODE}" = "false" ]; then \
        npm ci --legacy-peer-deps; \
    else \
        echo "Skipping 'npm ci' in dev mode"; \
    fi

# Runs the webpack build process
COPY ax-bi-frontend /app/ax-bi-frontend

######################################################################
# axbi-node is used for compiling frontend assets
######################################################################
FROM axbi-node-ci AS axbi-node

# Build the frontend if not in dev mode
RUN --mount=type=cache,target=/root/.npm \
    if [ "${DEV_MODE}" = "false" ]; then \
        echo "Running 'npm run ${BUILD_CMD}'"; \
        npm run ${BUILD_CMD}; \
    else \
        echo "Skipping 'npm run ${BUILD_CMD}' in dev mode"; \
    fi;

# Copy translation files
COPY axbi/translations /app/axbi/translations

# Build translations if enabled, then cleanup localization files
RUN if [ "${BUILD_TRANSLATIONS}" = "true" ]; then \
        npm run build-translation; \
    fi; \
    rm -rf /app/axbi/translations/*/*/*.po /app/axbi/translations/*/*/*.mo;


######################################################################
# Base python layer
######################################################################
FROM python:${PY_VER} AS python-base

ARG AXBI_HOME="/app/axbi_home"
ENV AXBI_HOME=${AXBI_HOME}

RUN mkdir -p ${AXBI_HOME}
RUN useradd --user-group -d ${AXBI_HOME} -m --no-log-init --shell /bin/bash axbi \
    && chmod -R 1777 ${AXBI_HOME} \
    && chown -R axbi:axbi ${AXBI_HOME}

# Some bash scripts needed throughout the layers
COPY --chmod=755 docker/*.sh /app/docker/

COPY --from=ghcr.io/astral-sh/uv:0.7.13 /uv /usr/local/bin/uv

# Using uv as it's faster/simpler than pip
RUN uv venv /app/.venv
ENV PATH="/app/.venv/bin:${PATH}"

######################################################################
# Python translation compiler layer
######################################################################
FROM python-base AS python-translation-compiler

ARG BUILD_TRANSLATIONS
ENV BUILD_TRANSLATIONS=${BUILD_TRANSLATIONS}

# Install Python dependencies using docker/pip-install.sh
COPY requirements/translations.txt requirements/
RUN --mount=type=cache,target=/root/.cache/uv \
    . /app/.venv/bin/activate && /app/docker/pip-install.sh --requires-build-essential -r requirements/translations.txt

COPY axbi/translations/ /app/translations_mo/
RUN if [ "${BUILD_TRANSLATIONS}" = "true" ]; then \
        pybabel compile -d /app/translations_mo | true; \
    fi; \
    rm -f /app/translations_mo/*/*/*.po /app/translations_mo/*/*/*.json

######################################################################
# Python APP common layer
######################################################################
FROM python-base AS python-common

ENV AXBI_HOME="/app/axbi_home" \
    HOME="/app/axbi_home" \
    AXBI_ENV="production" \
    FLASK_APP="axbi.app:create_app()" \
    PYTHONPATH="/app/pythonpath" \
    AXBI_PORT="8088"

# Copy the entrypoints, make them executable in userspace
COPY --chmod=755 docker/entrypoints /app/docker/entrypoints

WORKDIR /app
# Set up necessary directories
RUN mkdir -p \
      ${PYTHONPATH} \
      axbi/static \
      requirements \
      ax-bi-frontend \
      axbi.egg-info \
      requirements \
    && touch axbi/static/version_info.json

# Install Playwright and optionally setup headless browsers
ENV PLAYWRIGHT_BROWSERS_PATH=/usr/local/share/playwright-browsers

ARG INCLUDE_CHROMIUM="false"
ARG INCLUDE_FIREFOX="false"
RUN --mount=type=cache,target=${AXBI_HOME}/.cache/uv \
    if [ "${INCLUDE_CHROMIUM}" = "true" ] || [ "${INCLUDE_FIREFOX}" = "true" ]; then \
        uv pip install playwright && \
        playwright install-deps && \
        if [ "${INCLUDE_CHROMIUM}" = "true" ]; then playwright install chromium; fi && \
        if [ "${INCLUDE_FIREFOX}" = "true" ]; then playwright install firefox; fi; \
    else \
        echo "Skipping browser installation"; \
    fi

# Copy required files for Python build
COPY pyproject.toml setup.py MANIFEST.in README.md ./
COPY ax-bi-frontend/package.json ax-bi-frontend/
COPY scripts/check-env.py scripts/

# keeping for backward compatibility
COPY --chmod=755 ./docker/entrypoints/run-server.sh /usr/bin/

# Some debian libs
RUN /app/docker/apt-install.sh \
      curl \
      libsasl2-dev \
      libsasl2-modules-gssapi-mit \
      libpq-dev \
      libecpg-dev \
      libldap2-dev

# Create runtime data directories. Zero-config upload DuckDB files live under
# AXBI_HOME so named volumes persist them across container restarts.
RUN mkdir -p /app/data /app/axbi_home/uploads \
    && chown -R axbi:axbi /app/data /app/axbi_home/uploads

# Copy compiled things from previous stages
COPY --from=axbi-node /app/axbi/static/assets axbi/static/assets
# Copy service.worker.js optionall as it doesn't exist when DEV_MODE=true
COPY --from=axbi-node /app/axbi/static/service-worker.j[s] axbi/static/service-worker.js

# TODO, when the next version comes out, use --exclude axbi/translations
COPY axbi axbi
# Remove .po source files (only compiled .mo are needed at runtime) and
# create runtime upload directories in a single layer.
RUN rm -f axbi/translations/*/*/*.po \
    && mkdir -p /app/axbi_home/uploads axbi/static/uploads \
    && chown -R axbi:axbi \
        /app/data \
        /app/axbi_home/uploads \
        axbi/static/uploads

# Merging translations from backend and frontend stages
COPY --from=axbi-node /app/axbi/translations axbi/translations
COPY --from=python-translation-compiler /app/translations_mo axbi/translations

HEALTHCHECK CMD /app/docker/docker-healthcheck.sh
CMD ["/app/docker/entrypoints/run-server.sh"]
EXPOSE ${AXBI_PORT}

######################################################################
# Final lean image...
######################################################################
FROM python-common AS lean

LABEL maintainer="AX-BI <hello@defai.digital>"
LABEL org.opencontainers.image.title="AX-BI"
LABEL org.opencontainers.image.description="AX-BI — AI-powered data visualization platform"
LABEL org.opencontainers.image.source="https://github.com/defai-digital/ax-bi"
LABEL org.opencontainers.image.licenses="Apache-2.0"

# Install Python dependencies using docker/pip-install.sh
COPY requirements/base.txt requirements/

# Copy ax-bi-core package needed for editable install in base.txt
COPY ax-bi-core ax-bi-core
COPY docker/pythonpath_axbi/axbi_config.py /app/docker/pythonpath_axbi/axbi_config.py

RUN --mount=type=cache,target=${AXBI_HOME}/.cache/uv \
    /app/docker/pip-install.sh --requires-build-essential -r requirements/base.txt
# Install the axbi package
RUN --mount=type=cache,target=${AXBI_HOME}/.cache/uv \
    uv pip install -e .[duckdb,fastmcp,postgres]
RUN python -m compileall /app/axbi

USER axbi

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/docker/docker-healthcheck.sh

######################################################################
# Dev image...
######################################################################
FROM python-common AS dev

# Debian libs needed for dev
RUN /app/docker/apt-install.sh \
    git \
    pkg-config \
    default-libmysqlclient-dev

# Copy development requirements and install them
COPY requirements/*.txt requirements/

# Copy local packages needed for editable installs in development.txt
COPY ax-bi-core ax-bi-core
COPY ax-bi-extensions-cli ax-bi-extensions-cli

# Install Python dependencies using docker/pip-install.sh
RUN --mount=type=cache,target=${AXBI_HOME}/.cache/uv \
    /app/docker/pip-install.sh --requires-build-essential -r requirements/development.txt
# Install the axbi package
RUN --mount=type=cache,target=${AXBI_HOME}/.cache/uv \
    uv pip install -e .

RUN uv pip install .[postgres]
RUN python -m compileall /app/axbi

USER axbi

HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD /app/docker/docker-healthcheck.sh

######################################################################
# CI image...
######################################################################
FROM lean AS ci
USER root
RUN uv pip install .[postgres,duckdb]
USER axbi
CMD ["/app/docker/entrypoints/docker-ci.sh"]

######################################################################
# Showtime image - lean + DuckDB for examples database
######################################################################
FROM lean AS showtime
USER root
RUN uv pip install .[duckdb]
USER axbi
CMD ["/app/docker/entrypoints/docker-ci.sh"]
