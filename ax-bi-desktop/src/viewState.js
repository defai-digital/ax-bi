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

/**
 * Pure view-state rules for the AX BI desktop launcher.
 * Kept free of DOM so unit tests can exercise the real shipped logic.
 */

/**
 * Whether Desktop must hand the local admin credentials to the user before
 * opening the first-party AX BI webview.
 */
export function shouldShowLocalOnboarding(status) {
  return Boolean(
    status &&
      status.axbi_healthy &&
      status.onboarding_required &&
      status.admin_password_present,
  );
}

/**
 * Whether initial launcher status should hand off to an already healthy local
 * AX BI window. Explicitly returning to Desktop home remains sticky.
 */
export function shouldAutoOpenHealthyLocal({
  biSource,
  biVisible,
  busy,
  preferHomeView,
  status,
} = {}) {
  return Boolean(
    biSource === "local" &&
      !biVisible &&
      !busy &&
      !preferHomeView &&
      status?.axbi_healthy &&
      status.web_url,
  );
}

/**
 * Whether a healthy local instance went offline while the BI frame is open.
 */
export function shouldLeaveBiForOfflineLocal({
  biSource,
  biVisible,
  status,
} = {}) {
  return (
    biSource === "local" &&
    biVisible &&
    Boolean(status) &&
    !status.axbi_healthy
  );
}

/**
 * Prefer-home sticky flag after a navigation action.
 * @param {"showHome"|"showBiFrame"} action
 * @param {{ sticky?: boolean }} [options]
 */
export function nextPreferHomeView(action, options = {}) {
  if (action === "showBiFrame") {
    return false;
  }
  if (action === "showHome") {
    return options.sticky !== false;
  }
  return Boolean(options.preferHomeView);
}

/**
 * Summary line for the launcher home screen.
 */
export function summaryText(status) {
  if (!status) {
    return "Checking local runtime…";
  }
  if (status.axbi_healthy) {
    return "Local AX BI is ready";
  }
  if (status.axbi_running) {
    return "Local AX BI is starting";
  }
  if (status.stack_running) {
    return "Local AX BI needs attention — review diagnostics or stop and retry";
  }
  if (status.local_runtime_supported === false) {
    return "Local Docker runtime is not available on this platform";
  }
  const deps = Array.isArray(status.dependencies) ? status.dependencies : [];
  if (
    status.can_start_local === false ||
    (deps.length > 0 && !deps.every((dependency) => dependency.installed))
  ) {
    return "Install missing runtime dependencies to run local Docker";
  }
  if (status.configured) {
    return "Local Docker stack is prepared — start when ready";
  }
  return "Run locally (Docker) or connect to a server";
}

/**
 * Label shown in the web Settings → Desktop group.
 */
export function shellStatusLabel({ biSource, remoteBiUrl, status } = {}) {
  if (biSource === "remote" && remoteBiUrl) {
    try {
      return new URL(remoteBiUrl).host;
    } catch (error) {
      return "Connected";
    }
  }
  if (status && status.axbi_healthy) {
    return "Local · Ready";
  }
  if (status && status.axbi_running) {
    return "Local · Starting";
  }
  if (status && status.stack_running) {
    return "Local · Needs attention";
  }
  return "Local";
}
