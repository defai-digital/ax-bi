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
# Regression gate for prompt-to-dashboard generation. Runs a version-controlled
# golden prompt set through the *configured* generation pipeline (the LLM intent
# mapper if a provider is set, else the heuristic) and fails CI when governance
# compliance or intent-match regress. Requires a booted Superset with the target
# datasets indexed — run it in the app container / an integration job, e.g.:
#
#   docker compose exec superset scripts/semantic_index/eval_generation_ci.sh
#
# Each MANIFEST row is: dataset_id:golden_file:min_compliance:min_intent
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

MANIFEST=(
  "11:${HERE}/golden/service_revenue_2025.json:1.0:0.9"
)

status=0
for entry in "${MANIFEST[@]}"; do
  IFS=: read -r dataset_id golden min_compliance min_intent <<<"${entry}"
  echo "== generation eval: dataset ${dataset_id} (golden=${golden}) =="
  if ! superset semantic-index eval-generation \
      --dataset-id "${dataset_id}" \
      --cases-file "${golden}" \
      --fail-under "${min_compliance}" \
      --fail-under-intent "${min_intent}" \
      --no-persist; then
    echo "FAIL: dataset ${dataset_id} regressed below thresholds" >&2
    status=1
  fi
done

exit "${status}"
