#!/usr/bin/env bash

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
set -e

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'EOF'
Usage: ./scripts/python_tests.sh [pytest args...]

Upgrade the test database, initialize AxBI, load test users, and run
integration tests. Extra arguments are passed through to pytest.
EOF
  exit 0
fi

# Temporary fix, probably related with https://bugs.launchpad.net/ubuntu/+source/opencv/+bug/1890170
# MySQL was failing with:
# from . import _mysql
# ImportError: /lib/x86_64-linux-gnu/libstdc++.so.6: cannot allocate memory in static TLS block
export LD_PRELOAD=/lib/x86_64-linux-gnu/libstdc++.so.6
export AXBI_CONFIG=${AXBI_CONFIG:-tests.integration_tests.axbi_test_config}
export AX_BI_TESTENV=true
echo "AxBI config module: $AXBI_CONFIG"

ax-bi db upgrade
ax-bi init
ax-bi load-test-users

echo "Running tests"

pytest --durations-min=2 --cov-report= --cov=axbi ./tests/integration_tests "$@"
