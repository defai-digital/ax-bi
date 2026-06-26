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
REQUIRED_VERSIONS=("2" "3")
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "Usage: ./scripts/ci_check_npm_lock_version.sh <package-lock.json>"
    echo
    echo "Validate npm lockfileVersion is one of: ${REQUIRED_VERSIONS[*]}"
    exit 0
fi

if [[ ! -f "$1" ]]; then
    echo >&2 "Missing npm lock file: $1"
    exit 1
fi

LOCKFILE_VERSION=$(sed -n 's/[ \t]*"lockfileVersion"\: \([0-9]*\),/\1/p' "$1")

for REQUIRED_VERSION in "${REQUIRED_VERSIONS[@]}"; do
    if [[ $LOCKFILE_VERSION == "$REQUIRED_VERSION" ]]; then
        echo "Correct npm lock file version: $LOCKFILE_VERSION"
        exit 0
    fi
done

echo >&2 "Incorrect npm lock file version: $LOCKFILE_VERSION (Version ${REQUIRED_VERSIONS[*]} required)"
exit 1
