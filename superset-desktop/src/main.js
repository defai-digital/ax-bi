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

const LOCAL_RUNTIME_COMMANDS = [
  "prepare",
  "start",
  "stop",
  "restart",
  "update",
  "credentials",
  "refresh",
  "openLocal",
  "loadLogs",
];

const THEME_STORAGE_KEY = "ax-bi-theme-mode";
const THEME_MODES = new Set(["default", "dark", "system"]);
const SYSTEM_DARK_QUERY = "(prefers-color-scheme: dark)";
const DESKTOP_THEME_MESSAGE_SOURCE = "ax-bi-desktop";
const WEB_THEME_MESSAGE_SOURCE = "ax-bi-web";
const THEME_SET_MESSAGE_TYPE = "theme:set-mode";
const THEME_CHANGED_MESSAGE_TYPE = "theme:changed";

const elements = {
  activity: document.getElementById("activity"),
  biFrame: document.getElementById("biFrame"),
  biPanel: document.getElementById("biPanel"),
  biPlaceholder: document.getElementById("biPlaceholder"),
  biPlaceholderText: document.getElementById("biPlaceholderText"),
  biTab: document.getElementById("biTab"),
  busyBanner: document.getElementById("busyBanner"),
  busyMessage: document.getElementById("busyMessage"),
  colimaState: document.getElementById("colimaState"),
  credentials: document.getElementById("credentials"),
  credentialsBox: document.getElementById("credentialsBox"),
  dependencies: document.getElementById("dependencies"),
  dockerState: document.getElementById("dockerState"),
  healthState: document.getElementById("healthState"),
  loadLogs: document.getElementById("loadLogs"),
  logService: document.getElementById("logService"),
  logs: document.getElementById("logs"),
  mcpUrl: document.getElementById("mcpUrl"),
  openLocal: document.getElementById("openLocal"),
  prepare: document.getElementById("prepare"),
  refresh: document.getElementById("refresh"),
  restart: document.getElementById("restart"),
  runtimeDir: document.getElementById("runtimeDir"),
  runtimeState: document.getElementById("runtimeState"),
  serverUrl: document.getElementById("serverUrl"),
  settingsPanel: document.getElementById("settingsPanel"),
  settingsTab: document.getElementById("settingsTab"),
  start: document.getElementById("start"),
  stop: document.getElementById("stop"),
  summary: document.getElementById("summary"),
  themeControl: document.getElementById("themeControl"),
  themeOptions: document.querySelectorAll("[data-theme-mode]"),
  update: document.getElementById("update"),
  webUrl: document.getElementById("webUrl"),
};

let currentStatus = null;
let busy = false;
let biSource = "local";
let remoteBiUrl = null;
let currentThemeMode = "system";

function invoke(command, args = {}) {
  const internals = window.__TAURI_INTERNALS__;
  if (!internals || typeof internals.invoke !== "function") {
    return Promise.reject(
      new Error("AX BI Desktop native bridge is unavailable"),
    );
  }

  return internals.invoke(command, args);
}

function setActivity(message, variant = "neutral") {
  elements.activity.textContent = message;
  elements.activity.className = `activity ${variant ? `state-${variant}` : ""}`;
}

function setBusy(value, message) {
  busy = value;
  elements.busyBanner.classList.toggle("hidden", !value);
  if (message) {
    elements.busyMessage.textContent = message;
    elements.summary.textContent = message;
  }
  for (const id of LOCAL_RUNTIME_COMMANDS) {
    const element = elements[id];
    if (element) {
      element.disabled = value;
    }
  }
  if (message) {
    setActivity(message);
  }
  updateButtonState();
}

function switchTab(tab) {
  const isBi = tab === "bi";
  elements.biTab.classList.toggle("active", isBi);
  elements.settingsTab.classList.toggle("active", !isBi);
  elements.biTab.setAttribute("aria-selected", String(isBi));
  elements.settingsTab.setAttribute("aria-selected", String(!isBi));
  elements.biPanel.classList.toggle("active", isBi);
  elements.settingsPanel.classList.toggle("active", !isBi);
}

function showBiPlaceholder(message = "Use Settings to start AX BI.") {
  elements.biPlaceholderText.textContent = message;
  elements.biPlaceholder.classList.remove("hidden");
  elements.biFrame.classList.add("hidden");
  elements.biFrame.removeAttribute("src");
  elements.biFrame.dataset.url = "";
}

function showBiFrame(url) {
  elements.biPlaceholder.classList.add("hidden");
  elements.biFrame.classList.remove("hidden");
  if (elements.biFrame.dataset.url !== url) {
    elements.biFrame.dataset.url = url;
    elements.biFrame.src = url;
  }
  postThemeModeToBiFrame();
}

function renderBiView() {
  if (biSource === "remote" && remoteBiUrl) {
    showBiFrame(remoteBiUrl);
    return;
  }

  if (currentStatus && currentStatus.axbi_healthy && currentStatus.web_url) {
    showBiFrame(currentStatus.web_url);
    return;
  }

  showBiPlaceholder("Use Settings to start AX BI.");
}

function setState(element, label, variant) {
  element.textContent = label;
  element.className = variant ? `state-${variant}` : "";
}

function booleanState(value, yes, no) {
  return value ? [yes, "ok"] : [no, "bad"];
}

function renderStatus(status) {
  currentStatus = status;
  const runtime = status.axbi_running
    ? ["Running", "ok"]
    : status.configured
      ? ["Stopped", "warn"]
      : ["Not prepared", "warn"];
  const colima = booleanState(status.colima_running, "Running", "Stopped");
  const docker = booleanState(status.docker_ready, "Ready", "Unavailable");
  const health = status.axbi_healthy
    ? ["Healthy", "ok"]
    : status.axbi_running
      ? ["Starting", "warn"]
      : ["Offline", "bad"];

  setState(elements.runtimeState, runtime[0], runtime[1]);
  setState(elements.colimaState, colima[0], colima[1]);
  setState(elements.dockerState, docker[0], docker[1]);
  setState(elements.healthState, health[0], health[1]);

  elements.summary.textContent = summaryText(status);
  elements.runtimeDir.textContent = status.runtime_dir;
  elements.webUrl.value = status.web_url;
  elements.mcpUrl.value = status.mcp_url;
  renderDependencies(status.dependencies);
  updateButtonState();
  renderBiView();
}

function summaryText(status) {
  if (status.axbi_healthy) {
    return "Local AX BI is ready";
  }
  if (status.axbi_running) {
    return "Local AX BI is starting";
  }
  if (!status.dependencies.every((dependency) => dependency.installed)) {
    return "Install missing runtime dependencies";
  }
  if (status.configured) {
    return "Local runtime is prepared";
  }
  return "Local runtime is ready to prepare";
}

function renderDependencies(dependencies) {
  elements.dependencies.replaceChildren();
  if (!dependencies || dependencies.length === 0) {
    elements.dependencies.textContent = "No dependency information available.";
    return;
  }

  for (const dependency of dependencies) {
    const row = document.createElement("div");
    row.className = "dependency-row";

    const details = document.createElement("div");
    const title = document.createElement("div");
    title.className = "dependency-title";
    title.textContent = dependency.name;
    const version = document.createElement("div");
    version.className = "dependency-detail";
    version.textContent = dependency.installed
      ? dependency.version || dependency.command
      : dependency.install_hint;
    details.append(title, version);

    const pill = document.createElement("span");
    pill.className = dependency.installed ? "pill pill-ok" : "pill pill-bad";
    pill.textContent = dependency.installed ? "Installed" : "Missing";

    row.append(details, pill);
    elements.dependencies.append(row);
  }
}

function updateButtonState() {
  if (busy) {
    return;
  }
  const status = currentStatus;
  elements.openLocal.disabled = !status || !status.axbi_healthy;
  elements.credentials.disabled = !status || !status.admin_password_present;
  elements.stop.disabled = !status || !status.axbi_running;
  elements.restart.disabled = !status || !status.configured;
  elements.update.disabled = !status || !status.configured;
  elements.loadLogs.disabled =
    !status || !status.configured || !status.docker_ready;
}

async function refreshStatus(message) {
  if (message) {
    setActivity(message);
  }
  const status = await invoke("get_local_runtime_status");
  renderStatus(status);
  setActivity("Ready");
  return status;
}

async function runAction(message, command, after) {
  try {
    setBusy(true, message);
    await nextPaint();
    const result = await invoke(command);
    if (result && result.status) {
      renderStatus(result.status);
    }
    if (typeof after === "function") {
      await after(result);
    }
    setActivity("Ready", "ok");
  } catch (error) {
    const message = errorMessage(error);
    elements.summary.textContent = message;
    setActivity(message, "bad");
  } finally {
    setBusy(false);
  }
}

async function pollUntilHealthy() {
  for (let attempt = 0; attempt < 45; attempt += 1) {
    const status = await invoke("get_local_runtime_status");
    renderStatus(status);
    if (status.axbi_healthy) {
      setActivity("Local AX BI is ready", "ok");
      biSource = "local";
      renderBiView();
      switchTab("bi");
      return;
    }
    const message = status.axbi_running
      ? "Waiting for AX BI health checks"
      : "Waiting for containers to start";
    setActivity(message);
    elements.summary.textContent = message;
    await delay(2000);
  }
  setActivity("AX BI is still starting; refresh status in a moment", "warn");
}

function nextPaint() {
  return new Promise((resolve) => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(resolve);
    });
  });
}

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function errorMessage(error) {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === "string") {
    return error;
  }
  return "Unexpected desktop runtime error";
}

function isThemeMode(value) {
  return typeof value === "string" && THEME_MODES.has(value);
}

function normalizeThemeMode(value) {
  return isThemeMode(value) ? value : "system";
}

function readStoredThemeMode() {
  try {
    return normalizeThemeMode(window.localStorage.getItem(THEME_STORAGE_KEY));
  } catch (error) {
    return "system";
  }
}

function writeStoredThemeMode(mode) {
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, mode);
  } catch (error) {
    setActivity("Theme preference could not be saved", "warn");
  }
}

function resolveThemeMode(mode) {
  if (mode === "dark") {
    return "dark";
  }
  if (mode === "system") {
    return window.matchMedia?.(SYSTEM_DARK_QUERY).matches ? "dark" : "default";
  }
  return "default";
}

function updateThemeControl() {
  for (const option of elements.themeOptions) {
    const selected = option.dataset.themeMode === currentThemeMode;
    option.classList.toggle("active", selected);
    option.setAttribute("aria-pressed", String(selected));
  }
}

function applyThemeMode(mode, options = {}) {
  const { persist = true, notifyFrame = true } = options;
  currentThemeMode = normalizeThemeMode(mode);
  document.documentElement.dataset.themePreference = currentThemeMode;
  document.documentElement.dataset.themeMode =
    resolveThemeMode(currentThemeMode);
  updateThemeControl();

  if (persist) {
    writeStoredThemeMode(currentThemeMode);
  }
  if (notifyFrame) {
    postThemeModeToBiFrame();
  }
}

function frameTargetOrigin() {
  const url = elements.biFrame.dataset.url || elements.biFrame.src;
  if (!url) {
    return "*";
  }
  try {
    return new URL(url, window.location.href).origin;
  } catch (error) {
    return "*";
  }
}

function postThemeModeToBiFrame() {
  if (!elements.biFrame.contentWindow || !elements.biFrame.dataset.url) {
    return;
  }
  elements.biFrame.contentWindow.postMessage(
    {
      source: DESKTOP_THEME_MESSAGE_SOURCE,
      type: THEME_SET_MESSAGE_TYPE,
      mode: currentThemeMode,
    },
    frameTargetOrigin(),
  );
}

function handleThemeMessage(event) {
  if (event.source !== elements.biFrame.contentWindow) {
    return;
  }
  const data = event.data;
  if (
    !data ||
    data.source !== WEB_THEME_MESSAGE_SOURCE ||
    data.type !== THEME_CHANGED_MESSAGE_TYPE
  ) {
    return;
  }

  const mode = isThemeMode(data.mode) ? data.mode : data.resolvedMode;
  if (isThemeMode(mode)) {
    applyThemeMode(mode, { notifyFrame: false });
  }
}

function handleSystemThemeChange() {
  if (currentThemeMode === "system") {
    applyThemeMode("system", { persist: false });
  }
}

async function showCredentials() {
  try {
    setBusy(true, "Reading local admin credentials");
    await nextPaint();
    const credentials = await invoke("get_local_admin_credentials");
    elements.credentialsBox.classList.remove("hidden");
    elements.credentialsBox.textContent = `username: ${credentials.username}\npassword: ${credentials.password}`;
    setActivity("Credentials loaded", "ok");
  } catch (error) {
    const message = errorMessage(error);
    elements.summary.textContent = message;
    setActivity(message, "bad");
  } finally {
    setBusy(false);
  }
}

async function loadLogs() {
  try {
    setBusy(true, "Loading logs");
    await nextPaint();
    const service = elements.logService.value || null;
    elements.logs.textContent = await invoke("get_local_runtime_logs", {
      service,
      tail: 220,
    });
    setActivity("Logs loaded", "ok");
  } catch (error) {
    const message = errorMessage(error);
    elements.summary.textContent = message;
    setActivity(message, "bad");
  } finally {
    setBusy(false);
  }
}

function openLocalAxbi() {
  if (!currentStatus || !currentStatus.web_url) {
    setActivity("Local AX BI URL is unavailable", "bad");
    return;
  }
  biSource = "local";
  renderBiView();
  switchTab("bi");
}

function connectToServer(event) {
  event.preventDefault();
  const value = elements.serverUrl.value.trim();
  try {
    const url = new URL(value);
    if (url.protocol !== "http:" && url.protocol !== "https:") {
      throw new Error("Server URL must use http or https");
    }
    if (url.username || url.password) {
      throw new Error("Server URL must not include credentials");
    }
    remoteBiUrl = url.toString();
    biSource = "remote";
    renderBiView();
    switchTab("bi");
  } catch (error) {
    setActivity(errorMessage(error), "bad");
  }
}

function wireEvents() {
  elements.biTab.addEventListener("click", () => switchTab("bi"));
  elements.settingsTab.addEventListener("click", () => switchTab("settings"));
  elements.biFrame.addEventListener("load", postThemeModeToBiFrame);
  elements.biFrame.addEventListener("error", () => {
    if (biSource === "local") {
      showBiPlaceholder("Use Settings to start AX BI.");
    }
    setActivity("AX BI web app could not be loaded", "bad");
  });
  elements.refresh.addEventListener("click", () => {
    refreshStatus("Refreshing status").catch((error) => {
      const message = errorMessage(error);
      elements.summary.textContent = message;
      setActivity(message, "bad");
    });
  });
  elements.prepare.addEventListener("click", () => {
    runAction("Preparing local runtime", "prepare_local_runtime");
  });
  elements.start.addEventListener("click", () => {
    runAction("Starting local AX BI", "start_local_runtime", pollUntilHealthy);
  });
  elements.stop.addEventListener("click", () => {
    runAction("Stopping local AX BI", "stop_local_runtime");
  });
  elements.restart.addEventListener("click", () => {
    runAction(
      "Restarting local AX BI",
      "restart_local_runtime",
      pollUntilHealthy,
    );
  });
  elements.update.addEventListener("click", () => {
    runAction(
      "Updating local AX BI images",
      "update_local_runtime",
      pollUntilHealthy,
    );
  });
  elements.credentials.addEventListener("click", showCredentials);
  elements.openLocal.addEventListener("click", openLocalAxbi);
  elements.loadLogs.addEventListener("click", loadLogs);
  elements.themeControl.addEventListener("click", (event) => {
    const option = event.target.closest("[data-theme-mode]");
    if (!option) {
      return;
    }
    applyThemeMode(option.dataset.themeMode);
  });
  document
    .getElementById("connectForm")
    .addEventListener("submit", connectToServer);
  window.addEventListener("message", handleThemeMessage);
  window
    .matchMedia?.(SYSTEM_DARK_QUERY)
    .addEventListener("change", handleSystemThemeChange);
}

applyThemeMode(readStoredThemeMode(), { persist: false, notifyFrame: false });
wireEvents();
renderBiView();
refreshStatus("Checking local runtime").catch((error) => {
  const message = errorMessage(error);
  elements.summary.textContent = message;
  renderBiView();
  setActivity(message, "bad");
});
