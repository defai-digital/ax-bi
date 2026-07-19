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

# Python version installed; we need 3.12
PYTHON=`command -v python3.12`
# Keep uv and Makefile on the same env (docs/Makefile use venv/, not .venv/)
export UV_PROJECT_ENVIRONMENT := venv
MIN_PYTHON_MINOR := 12

.PHONY: install axbi venv venv-recreate pre-commit up down logs ps nuke ports open

install: axbi pre-commit

axbi: venv
	# Bootstrap uv (the project's installer) into the active environment
	. venv/bin/activate && pip install uv

	# Install external dependencies
	. venv/bin/activate && uv pip install -r requirements/development.txt

	# Install AxBI in editable (development) mode
	. venv/bin/activate && uv pip install -e .

	# Create an admin user in your metadata database
	. venv/bin/activate && ax-bi fab create-admin \
                    --username admin \
                    --firstname "Admin I."\
                    --lastname Strator \
                    --email admin@axbi.io \
                    --password general

	# Initialize the database
	. venv/bin/activate && ax-bi db upgrade

	# Create default roles and permissions
	. venv/bin/activate && ax-bi init

	# Load some data to play with
	. venv/bin/activate && ax-bi load-examples

	# Install node packages
	cd ax-bi-frontend; npm ci

update: update-py update-js

update-py: venv
	# Bootstrap uv (the project's installer) into the active environment
	. venv/bin/activate && pip install uv

	# Install external dependencies
	. venv/bin/activate && uv pip install -r requirements/development.txt

	# Install AxBI in editable (development) mode
	. venv/bin/activate && uv pip install -e .

	# Initialize the database
	. venv/bin/activate && ax-bi db upgrade

	# Create default roles and permissions
	. venv/bin/activate && ax-bi init

update-js:
	# Install js packages
	cd ax-bi-frontend; npm ci

# Ensure ./venv exists and is Python 3.12+. Does not recreate a good env.
venv:
	@if ! [ -x "${PYTHON}" ]; then \
		echo "error: Python 3.12 is required (python3.12 not found on PATH)"; \
		exit 1; \
	fi
	@if [ ! -d venv ]; then \
		echo "Creating venv with $$($(PYTHON) --version)..."; \
		${PYTHON} -m venv venv; \
	fi
	@venv_ver=$$(venv/bin/python -c 'import sys; print(f"{sys.version_info[0]}.{sys.version_info[1]}")'); \
	venv_minor=$$(venv/bin/python -c 'import sys; print(sys.version_info[1])'); \
	if [ "$$(venv/bin/python -c 'import sys; print(sys.version_info[0])')" != "3" ] \
		|| [ "$$venv_minor" -lt "$(MIN_PYTHON_MINOR)" ]; then \
		echo "error: ./venv is Python $$venv_ver but AX BI requires Python 3.$(MIN_PYTHON_MINOR)+"; \
		echo "hint: run 'make venv-recreate' then reinstall deps (e.g. make update-py)"; \
		exit 1; \
	fi
	@echo "venv OK: $$(venv/bin/python --version) ($$(pwd)/venv)"

# Destroy and recreate ./venv with Python 3.12. Reinstall packages afterwards.
venv-recreate:
	@if ! [ -x "${PYTHON}" ]; then \
		echo "error: Python 3.12 is required (python3.12 not found on PATH)"; \
		exit 1; \
	fi
	@echo "Removing existing ./venv (if any)..."
	rm -rf venv
	@echo "Creating venv with $$($(PYTHON) --version)..."
	@${PYTHON} -m venv venv
	@echo "venv recreated: $$(venv/bin/python --version)"
	@echo "Next: source venv/bin/activate && make update-py  # or: make install"

activate: venv
	@echo "Run: source venv/bin/activate"
	@echo "Active interpreter should be: $$(pwd)/venv/bin/python"

pre-commit: venv
	# setup pre commit dependencies
	. venv/bin/activate && pip install uv
	. venv/bin/activate && uv pip install -r requirements/development.txt
	. venv/bin/activate && pre-commit install

format: py-format js-format

py-format: pre-commit
	pre-commit run black --all-files

js-format:
	cd ax-bi-frontend; npm run prettier

flask-app:
	flask run -p 31423 --reload --debugger

node-app:
	cd ax-bi-frontend; npm run dev-server

build-cypress:
	cd ax-bi-frontend; npm run build-instrumented
	cd ax-bi-frontend/cypress-base; npm ci

open-cypress:
	if ! [ $(port) ]; then cd ax-bi-frontend/cypress-base; CYPRESS_BASE_URL=http://localhost:31422 npm run cypress open; fi
	cd ax-bi-frontend/cypress-base; CYPRESS_BASE_URL=http://localhost:$(port) npm run cypress open

report-celery-worker:
	celery --app=axbi.tasks.celery_app:app worker

report-celery-beat:
	celery --app=axbi.tasks.celery_app:app beat --pidfile /tmp/celerybeat.pid --schedule /tmp/celerybeat-schedulecd

admin-user:
	ax-bi fab create-admin

# Docker Compose with auto-assigned ports (for running multiple instances)
up:
	./scripts/docker-compose-up.sh

up-detached:
	./scripts/docker-compose-up.sh -d

down:
	./scripts/docker-compose-up.sh down

logs:
	./scripts/docker-compose-up.sh logs -f

ps:
	./scripts/docker-compose-up.sh ps

nuke:
	./scripts/docker-compose-up.sh nuke

ports:
	./scripts/docker-compose-up.sh ports

open:
	./scripts/docker-compose-up.sh open
