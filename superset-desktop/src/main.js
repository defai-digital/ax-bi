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
  "pathLocal",
];

const THEME_STORAGE_KEY = "ax-bi-theme-mode";
const REMOTE_URL_STORAGE_KEY = "ax-bi-remote-url";
const THEME_MODES = new Set(["default", "dark", "system"]);
const SYSTEM_DARK_QUERY = "(prefers-color-scheme: dark)";
const DESKTOP_THEME_MESSAGE_SOURCE = "ax-bi-desktop";
const WEB_THEME_MESSAGE_SOURCE = "ax-bi-web";
const THEME_SET_MESSAGE_TYPE = "theme:set-mode";
const THEME_CHANGED_MESSAGE_TYPE = "theme:changed";
const SHELL_HELLO_MESSAGE_TYPE = "shell:hello";
const SHELL_OPEN_HOME_MESSAGE_TYPE = "shell:open-home";
const SHELL_OPEN_SETTINGS_MESSAGE_TYPE = "shell:open-settings";

const elements = {
  activity: document.getElementById("activity"),
  advancedPanel: document.getElementById("advancedPanel"),
  appShell: document.getElementById("appShell"),
  biFrame: document.getElementById("biFrame"),
  biStage: document.getElementById("biStage"),
  busyBanner: document.getElementById("busyBanner"),
  busyMessage: document.getElementById("busyMessage"),
  closeSettings: document.getElementById("closeSettings"),
  colimaState: document.getElementById("colimaState"),
  copyCredentials: document.getElementById("copyCredentials"),
  credentials: document.getElementById("credentials"),
  credentialsBox: document.getElementById("credentialsBox"),
  credentialsToast: document.getElementById("credentialsToast"),
  credentialsToastText: document.getElementById("credentialsToastText"),
  dependencies: document.getElementById("dependencies"),
  dismissCredentials: document.getElementById("dismissCredentials"),
  dockerState: document.getElementById("dockerState"),
  healthState: document.getElementById("healthState"),
  frameControls: document.getElementById("frameControls"),
  homeOpenSettings: document.getElementById("homeOpenSettings"),
  homeView: document.getElementById("homeView"),
  loadLogs: document.getElementById("loadLogs"),
  localPathDesc: document.getElementById("localPathDesc"),
  localPathTitle: document.getElementById("localPathTitle"),
  logService: document.getElementById("logService"),
  logs: document.getElementById("logs"),
  mcpUrl: document.getElementById("mcpUrl"),
  openHome: document.getElementById("openHome"),
  openLocal: document.getElementById("openLocal"),
  openSettings: document.getElementById("openSettings"),
  pathConnect: document.getElementById("pathConnect"),
  pathLocal: document.getElementById("pathLocal"),
  prepare: document.getElementById("prepare"),
  refresh: document.getElementById("refresh"),
  restart: document.getElementById("restart"),
  runtimeDir: document.getElementById("runtimeDir"),
  runtimeState: document.getElementById("runtimeState"),
  serverUrl: document.getElementById("serverUrl"),
  settingsBackdrop: document.getElementById("settingsBackdrop"),
  settingsOverlay: document.getElementById("settingsOverlay"),
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
let biVisible = false;
// When true, stay on the launcher home even if local BI is healthy.
// Cleared when the user explicitly opens BI (local or remote).
let preferHomeView = false;

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
  if (!elements.activity) {
    return;
  }
  elements.activity.textContent = message;
  elements.activity.className = `activity ${variant ? `state-${variant}` : ""}`;
}

function setBusy(value, message) {
  busy = value;
  elements.busyBanner.classList.toggle("hidden", !value);
  if (message) {
    elements.busyMessage.textContent = message;
    if (elements.summary) {
      elements.summary.textContent = message;
    }
  }
  for (const id of LOCAL_RUNTIME_COMMANDS) {
    const element = elements[id];
    if (element) {
      element.disabled = value;
    }
  }
  if (elements.pathConnect) {
    elements.pathConnect.disabled = value;
  }
  if (message) {
    setActivity(message);
  }
  updateButtonState();
}

function openSettings() {
  elements.settingsOverlay.classList.remove("hidden");
  elements.closeSettings.focus();
}

function closeSettings() {
  elements.settingsOverlay.classList.add("hidden");
}

function isSettingsOpen() {
  return !elements.settingsOverlay.classList.contains("hidden");
}

function setBiActive(visible) {
  elements.appShell.classList.toggle("bi-active", visible);
  if (elements.frameControls) {
    elements.frameControls.classList.toggle("hidden", !visible);
  }
}

function shellStatusLabel() {
  if (biSource === "remote" && remoteBiUrl) {
    try {
      return new URL(remoteBiUrl).host;
    } catch (error) {
      return "Connected";
    }
  }
  if (currentStatus && currentStatus.axbi_healthy) {
    return "Local · Ready";
  }
  if (currentStatus && currentStatus.axbi_running) {
    return "Local · Starting";
  }
  return "Local";
}

function showHome(message, options = {}) {
  const { sticky = true } = options;
  biVisible = false;
  // sticky=true keeps the user on the launcher after Desktop home / offline.
  // sticky=false is for the initial boot screen so auto-open can still run.
  preferHomeView = sticky;
  elements.homeView.classList.remove("hidden");
  elements.biFrame.classList.add("hidden");
  elements.biFrame.removeAttribute("src");
  elements.biFrame.dataset.url = "";
  setBiActive(false);
  if (message) {
    elements.summary.textContent = message;
  }
}

function showBiFrame(url) {
  biVisible = true;
  preferHomeView = false;
  elements.homeView.classList.add("hidden");
  elements.biFrame.classList.remove("hidden");
  setBiActive(true);
  if (elements.biFrame.dataset.url !== url) {
    elements.biFrame.dataset.url = url;
    elements.biFrame.src = url;
  }
  postThemeModeToBiFrame();
  postShellHelloToBiFrame();
}

function renderBiView() {
  if (preferHomeView) {
    showHome(summaryText(currentStatus));
    return;
  }

  if (biSource === "remote" && remoteBiUrl) {
    showBiFrame(remoteBiUrl);
    return;
  }

  if (currentStatus && currentStatus.axbi_healthy && currentStatus.web_url) {
    showBiFrame(currentStatus.web_url);
    return;
  }

  showHome(summaryText(currentStatus), { sticky: false });
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

  if (elements.summary && !biVisible) {
    elements.summary.textContent = summaryText(status);
  }
  elements.runtimeDir.textContent = status.runtime_dir
    ? `Runtime: ${status.runtime_dir}`
    : "Runtime directory pending";
  elements.webUrl.value = status.web_url;
  elements.mcpUrl.value = status.mcp_url;
  renderDependencies(status.dependencies);
  updateLocalPathCopy(status);
  updateButtonState();
  if (biVisible) {
    postShellHelloToBiFrame();
  }

  // Only auto-switch to BI when local is healthy and user is on local source.
  // Do not yank the user out of a remote session or Desktop home on status refresh.
  if (biSource === "local") {
    if (status.axbi_healthy && status.web_url && !preferHomeView) {
      showBiFrame(status.web_url);
    } else if (biVisible && !status.axbi_healthy) {
      // Local went offline while viewing it.
      showHome(summaryText(status));
    } else if (!biVisible && elements.summary) {
      elements.summary.textContent = summaryText(status);
    }
  }
}

function updateLocalPathCopy(status) {
  if (!elements.localPathTitle || !elements.localPathDesc) {
    return;
  }
  if (status.axbi_healthy) {
    elements.localPathTitle.textContent = "Open local AX BI";
    elements.localPathDesc.textContent =
      "Local instance is running. Open it in this window.";
    return;
  }
  if (status.axbi_running) {
    elements.localPathTitle.textContent = "Local AX BI is starting";
    elements.localPathDesc.textContent =
      "Docker containers are coming up. This usually takes a minute.";
    return;
  }
  if (status.configured) {
    elements.localPathTitle.textContent = "Start local AX BI";
    elements.localPathDesc.textContent =
      "Local runtime is prepared. Start the Docker stack on this Mac.";
    return;
  }
  elements.localPathTitle.textContent = "Run locally";
  elements.localPathDesc.textContent =
    "Prepare and start AX BI with the app-managed Docker runtime.";
}

function summaryText(status) {
  if (!status) {
    return "Checking local runtime…";
  }
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
    return "Local runtime is prepared — start when ready";
  }
  return "Run locally or connect to a server";
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
  if (elements.pathLocal) {
    elements.pathLocal.disabled = false;
  }
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
    } else if (result && typeof result === "object" && "axbi_healthy" in result) {
      // prepare returns status directly
      renderStatus(result);
    }
    if (typeof after === "function") {
      await after(result);
    }
    setActivity("Ready", "ok");
    return result;
  } catch (error) {
    const errMessage = errorMessage(error);
    if (elements.summary) {
      elements.summary.textContent = errMessage;
    }
    setActivity(errMessage, "bad");
    throw error;
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
      showBiFrame(status.web_url);
      closeSettings();
      const credentials = await loadCredentialsQuietly();
      if (credentials) {
        showCredentialsToast(credentials);
      }
      return;
    }
    const message = status.axbi_running
      ? "Waiting for AX BI health checks"
      : "Waiting for containers to start";
    setActivity(message);
    if (elements.summary) {
      elements.summary.textContent = message;
    }
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

function readStoredRemoteUrl() {
  try {
    return window.localStorage.getItem(REMOTE_URL_STORAGE_KEY) || "";
  } catch (error) {
    return "";
  }
}

function writeStoredRemoteUrl(url) {
  try {
    if (url) {
      window.localStorage.setItem(REMOTE_URL_STORAGE_KEY, url);
    }
  } catch (error) {
    // Non-fatal.
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

function postShellHelloToBiFrame() {
  if (!elements.biFrame.contentWindow || !elements.biFrame.dataset.url) {
    return;
  }
  elements.biFrame.contentWindow.postMessage(
    {
      source: DESKTOP_THEME_MESSAGE_SOURCE,
      type: SHELL_HELLO_MESSAGE_TYPE,
      status: shellStatusLabel(),
    },
    frameTargetOrigin(),
  );
}

function handleWebMessage(event) {
  if (event.source !== elements.biFrame.contentWindow) {
    return;
  }
  const data = event.data;
  if (!data || data.source !== WEB_THEME_MESSAGE_SOURCE) {
    return;
  }

  if (data.type === THEME_CHANGED_MESSAGE_TYPE) {
    const mode = isThemeMode(data.mode) ? data.mode : data.resolvedMode;
    if (isThemeMode(mode)) {
      applyThemeMode(mode, { notifyFrame: false });
    }
    return;
  }

  if (data.type === SHELL_OPEN_HOME_MESSAGE_TYPE) {
    goHome();
    return;
  }

  if (data.type === SHELL_OPEN_SETTINGS_MESSAGE_TYPE) {
    openSettings();
  }
}

function handleSystemThemeChange() {
  if (currentThemeMode === "system") {
    applyThemeMode("system", { persist: false });
  }
}

function formatCredentials(credentials) {
  return `username: ${credentials.username}\npassword: ${credentials.password}`;
}

function showCredentialsToast(credentials) {
  if (!elements.credentialsToast || !elements.credentialsToastText) {
    return;
  }
  const text = formatCredentials(credentials);
  elements.credentialsToastText.textContent = text;
  elements.credentialsBox.classList.remove("hidden");
  elements.credentialsBox.textContent = text;
  elements.credentialsToast.classList.remove("hidden");
}

function hideCredentialsToast() {
  if (elements.credentialsToast) {
    elements.credentialsToast.classList.add("hidden");
  }
}

async function loadCredentialsQuietly() {
  if (!currentStatus || !currentStatus.admin_password_present) {
    return null;
  }
  try {
    return await invoke("get_local_admin_credentials");
  } catch (error) {
    return null;
  }
}

async function showCredentials() {
  try {
    setBusy(true, "Reading local admin credentials");
    await nextPaint();
    const credentials = await invoke("get_local_admin_credentials");
    showCredentialsToast(credentials);
    setActivity("Credentials loaded", "ok");
  } catch (error) {
    const message = errorMessage(error);
    if (elements.summary) {
      elements.summary.textContent = message;
    }
    setActivity(message, "bad");
  } finally {
    setBusy(false);
  }
}

async function copyCredentialsToClipboard() {
  const text =
    elements.credentialsToastText?.textContent ||
    elements.credentialsBox?.textContent ||
    "";
  if (!text) {
    setActivity("No credentials to copy", "warn");
    return;
  }
  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      throw new Error("Clipboard API unavailable");
    }
    setActivity("Credentials copied", "ok");
  } catch (error) {
    setActivity("Could not copy credentials", "warn");
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
    if (elements.summary) {
      elements.summary.textContent = message;
    }
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
  showBiFrame(currentStatus.web_url);
  closeSettings();
}

function goHome() {
  // Keep biSource as-is for "Run locally" / Connect defaults; only leave the BI view.
  showHome(summaryText(currentStatus));
  closeSettings();
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
    writeStoredRemoteUrl(remoteBiUrl);
    showBiFrame(remoteBiUrl);
    closeSettings();
    setActivity("Connected", "ok");
  } catch (error) {
    setActivity(errorMessage(error), "bad");
  }
}

function focusConnect() {
  openSettings();
  elements.serverUrl.focus();
  elements.serverUrl.select();
}

function missingDependencies(status) {
  if (!status || !Array.isArray(status.dependencies)) {
    return [];
  }
  return status.dependencies.filter((dependency) => !dependency.installed);
}

function openAdvancedSettings() {
  openSettings();
  if (elements.advancedPanel) {
    elements.advancedPanel.open = true;
  }
}

async function startLocalFromHome() {
  if (currentStatus && currentStatus.axbi_healthy && currentStatus.web_url) {
    biSource = "local";
    showBiFrame(currentStatus.web_url);
    const credentials = await loadCredentialsQuietly();
    if (credentials) {
      showCredentialsToast(credentials);
    }
    return;
  }

  const missing = missingDependencies(currentStatus);
  if (missing.length > 0) {
    const names = missing.map((dependency) => dependency.name).join(", ");
    const message = `Install missing tools first: ${names}`;
    if (elements.summary) {
      elements.summary.textContent = message;
    }
    setActivity(message, "bad");
    openAdvancedSettings();
    return;
  }

  // Prepare if needed, then start, then poll.
  try {
    if (!currentStatus || !currentStatus.configured) {
      await runAction("Preparing local runtime", "prepare_local_runtime");
    }
    await runAction(
      "Starting local AX BI",
      "start_local_runtime",
      pollUntilHealthy,
    );
  } catch (error) {
    // runAction already surfaces errors; open advanced for recovery.
    openAdvancedSettings();
  }
}

function wireEvents() {
  elements.homeOpenSettings.addEventListener("click", openSettings);
  elements.closeSettings.addEventListener("click", closeSettings);
  elements.settingsBackdrop.addEventListener("click", closeSettings);
  elements.openHome?.addEventListener("click", goHome);
  elements.openSettings?.addEventListener("click", openSettings);

  elements.pathConnect.addEventListener("click", focusConnect);
  elements.pathLocal.addEventListener("click", () => {
    startLocalFromHome();
  });

  elements.biFrame.addEventListener("load", () => {
    postThemeModeToBiFrame();
    postShellHelloToBiFrame();
  });
  elements.biFrame.addEventListener("error", () => {
    if (biSource === "local") {
      showHome("Use Settings to start AX BI.");
    }
    setActivity("AX BI web app could not be loaded", "bad");
  });

  elements.refresh.addEventListener("click", () => {
    refreshStatus("Refreshing status").catch((error) => {
      const message = errorMessage(error);
      if (elements.summary) {
        elements.summary.textContent = message;
      }
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
  elements.copyCredentials?.addEventListener("click", copyCredentialsToClipboard);
  elements.dismissCredentials?.addEventListener("click", hideCredentialsToast);
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

  window.addEventListener("message", handleWebMessage);
  window
    .matchMedia?.(SYSTEM_DARK_QUERY)
    .addEventListener("change", handleSystemThemeChange);

  window.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isSettingsOpen()) {
      closeSettings();
    }
    // Desktop shortcuts when BI is full-bleed (no separate chrome bar).
    const meta = event.metaKey || event.ctrlKey;
    if (meta && event.key === ",") {
      event.preventDefault();
      openSettings();
    }
    if (meta && event.shiftKey && (event.key === "h" || event.key === "H")) {
      event.preventDefault();
      goHome();
    }
  });
}

// Restore last remote URL into the form (do not auto-connect).
const storedRemote = readStoredRemoteUrl();
if (storedRemote && elements.serverUrl) {
  elements.serverUrl.value = storedRemote;
}

applyThemeMode(readStoredThemeMode(), { persist: false, notifyFrame: false });
wireEvents();
showHome("Checking local runtime…", { sticky: false });
refreshStatus("Checking local runtime").catch((error) => {
  const message = errorMessage(error);
  if (elements.summary) {
    elements.summary.textContent = message;
  }
  showHome(message, { sticky: false });
  setActivity(message, "bad");
});
