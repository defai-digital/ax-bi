/*
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

import assert from "node:assert/strict";
import test from "node:test";
import {
  nextPreferHomeView,
  shellStatusLabel,
  shouldShowLocalOnboarding,
  shouldLeaveBiForOfflineLocal,
  summaryText,
} from "./viewState.js";

test("shouldShowLocalOnboarding requires a healthy runtime and credentials", () => {
  assert.equal(
    shouldShowLocalOnboarding({
      axbi_healthy: true,
      onboarding_required: true,
      admin_password_present: true,
    }),
    true,
  );
  assert.equal(
    shouldShowLocalOnboarding({
      axbi_healthy: true,
      onboarding_required: false,
      admin_password_present: true,
    }),
    false,
  );
  assert.equal(
    shouldShowLocalOnboarding({
      axbi_healthy: false,
      onboarding_required: true,
      admin_password_present: true,
    }),
    false,
  );
});

test("shouldLeaveBiForOfflineLocal only when viewing local that went offline", () => {
  assert.equal(
    shouldLeaveBiForOfflineLocal({
      biSource: "local",
      biVisible: true,
      status: { axbi_healthy: false },
    }),
    true,
  );
  assert.equal(
    shouldLeaveBiForOfflineLocal({
      biSource: "remote",
      biVisible: true,
      status: { axbi_healthy: false },
    }),
    false,
  );
  assert.equal(
    shouldLeaveBiForOfflineLocal({
      biSource: "local",
      biVisible: false,
      status: { axbi_healthy: false },
    }),
    false,
  );
});

test("nextPreferHomeView sticky rules", () => {
  assert.equal(nextPreferHomeView("showBiFrame"), false);
  assert.equal(nextPreferHomeView("showHome"), true);
  assert.equal(nextPreferHomeView("showHome", { sticky: false }), false);
  assert.equal(nextPreferHomeView("showHome", { sticky: true }), true);
});

test("summaryText is safe without dependencies array", () => {
  assert.equal(summaryText(null), "Checking local runtime…");
  assert.equal(
    summaryText({ axbi_healthy: true }),
    "Local AX BI is ready",
  );
  assert.equal(
    summaryText({
      axbi_healthy: false,
      axbi_running: false,
      configured: false,
      local_runtime_supported: true,
      can_start_local: true,
    }),
    "Run locally (Docker) or connect to a server",
  );
  assert.equal(
    summaryText({
      axbi_healthy: false,
      axbi_running: false,
      configured: false,
      dependencies: [{ installed: false }],
      can_start_local: false,
    }),
    "Install missing runtime dependencies to run local Docker",
  );
});

test("shellStatusLabel prefers remote host then local health", () => {
  assert.equal(
    shellStatusLabel({
      biSource: "remote",
      remoteBiUrl: "https://bi.example.com/path",
    }),
    "bi.example.com",
  );
  assert.equal(
    shellStatusLabel({
      biSource: "local",
      status: { axbi_healthy: true },
    }),
    "Local · Ready",
  );
  assert.equal(shellStatusLabel({ biSource: "local" }), "Local");
});
