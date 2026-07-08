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
  'prepare',
  'start',
  'stop',
  'restart',
  'update',
  'credentials',
  'refresh',
  'openLocal',
  'loadLogs',
];

const elements = {
  activity: document.getElementById('activity'),
  colimaState: document.getElementById('colimaState'),
  credentials: document.getElementById('credentials'),
  credentialsBox: document.getElementById('credentialsBox'),
  dependencies: document.getElementById('dependencies'),
  dockerState: document.getElementById('dockerState'),
  healthState: document.getElementById('healthState'),
  loadLogs: document.getElementById('loadLogs'),
  logService: document.getElementById('logService'),
  logs: document.getElementById('logs'),
  mcpUrl: document.getElementById('mcpUrl'),
  openLocal: document.getElementById('openLocal'),
  prepare: document.getElementById('prepare'),
  refresh: document.getElementById('refresh'),
  restart: document.getElementById('restart'),
  runtimeDir: document.getElementById('runtimeDir'),
  runtimeState: document.getElementById('runtimeState'),
  serverUrl: document.getElementById('serverUrl'),
  start: document.getElementById('start'),
  stop: document.getElementById('stop'),
  summary: document.getElementById('summary'),
  update: document.getElementById('update'),
  webUrl: document.getElementById('webUrl'),
};

let currentStatus = null;
let busy = false;

function invoke(command, args = {}) {
  const internals = window.__TAURI_INTERNALS__;
  if (!internals || typeof internals.invoke !== 'function') {
    return Promise.reject(
      new Error('AX-BI Desktop native bridge is unavailable'),
    );
  }

  return internals.invoke(command, args);
}

function setActivity(message, variant = 'neutral') {
  elements.activity.textContent = message;
  elements.activity.className = `activity ${variant ? `state-${variant}` : ''}`;
}

function setBusy(value, message) {
  busy = value;
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

function setState(element, label, variant) {
  element.textContent = label;
  element.className = variant ? `state-${variant}` : '';
}

function booleanState(value, yes, no) {
  return value ? [yes, 'ok'] : [no, 'bad'];
}

function renderStatus(status) {
  currentStatus = status;
  const runtime = status.axbi_running
    ? ['Running', 'ok']
    : status.configured
      ? ['Stopped', 'warn']
      : ['Not prepared', 'warn'];
  const colima = booleanState(status.colima_running, 'Running', 'Stopped');
  const docker = booleanState(status.docker_ready, 'Ready', 'Unavailable');
  const health = status.axbi_healthy
    ? ['Healthy', 'ok']
    : status.axbi_running
      ? ['Starting', 'warn']
      : ['Offline', 'bad'];

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
}

function summaryText(status) {
  if (status.axbi_healthy) {
    return 'Local AX-BI is ready';
  }
  if (status.axbi_running) {
    return 'Local AX-BI is starting';
  }
  if (!status.dependencies.every(dependency => dependency.installed)) {
    return 'Install missing runtime dependencies';
  }
  if (status.configured) {
    return 'Local runtime is prepared';
  }
  return 'Local runtime is ready to prepare';
}

function renderDependencies(dependencies) {
  elements.dependencies.replaceChildren();
  if (!dependencies || dependencies.length === 0) {
    elements.dependencies.textContent = 'No dependency information available.';
    return;
  }

  for (const dependency of dependencies) {
    const row = document.createElement('div');
    row.className = 'dependency-row';

    const details = document.createElement('div');
    const title = document.createElement('div');
    title.className = 'dependency-title';
    title.textContent = dependency.name;
    const version = document.createElement('div');
    version.className = 'dependency-detail';
    version.textContent = dependency.installed
      ? dependency.version || dependency.command
      : dependency.install_hint;
    details.append(title, version);

    const pill = document.createElement('span');
    pill.className = dependency.installed ? 'pill pill-ok' : 'pill pill-bad';
    pill.textContent = dependency.installed ? 'Installed' : 'Missing';

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
  elements.loadLogs.disabled = !status || !status.configured || !status.docker_ready;
}

async function refreshStatus(message) {
  if (message) {
    setActivity(message);
  }
  const status = await invoke('get_local_runtime_status');
  renderStatus(status);
  setActivity('Ready');
  return status;
}

async function runAction(message, command, after) {
  try {
    setBusy(true, message);
    const result = await invoke(command);
    if (result && result.status) {
      renderStatus(result.status);
    }
    if (typeof after === 'function') {
      await after(result);
    }
    setActivity('Ready', 'ok');
  } catch (error) {
    setActivity(errorMessage(error), 'bad');
  } finally {
    setBusy(false);
  }
}

async function pollUntilHealthy() {
  for (let attempt = 0; attempt < 45; attempt += 1) {
    const status = await invoke('get_local_runtime_status');
    renderStatus(status);
    if (status.axbi_healthy) {
      setActivity('Local AX-BI is ready', 'ok');
      return;
    }
    setActivity('Waiting for AX-BI health checks');
    await delay(2000);
  }
  setActivity('AX-BI is still starting; refresh status in a moment', 'warn');
}

function delay(ms) {
  return new Promise(resolve => {
    window.setTimeout(resolve, ms);
  });
}

function errorMessage(error) {
  if (error instanceof Error) {
    return error.message;
  }
  if (typeof error === 'string') {
    return error;
  }
  return 'Unexpected desktop runtime error';
}

async function showCredentials() {
  try {
    setBusy(true, 'Reading local admin credentials');
    const credentials = await invoke('get_local_admin_credentials');
    elements.credentialsBox.classList.remove('hidden');
    elements.credentialsBox.textContent = `username: ${credentials.username}\npassword: ${credentials.password}`;
    setActivity('Credentials loaded', 'ok');
  } catch (error) {
    setActivity(errorMessage(error), 'bad');
  } finally {
    setBusy(false);
  }
}

async function loadLogs() {
  try {
    setBusy(true, 'Loading logs');
    const service = elements.logService.value || null;
    elements.logs.textContent = await invoke('get_local_runtime_logs', {
      service,
      tail: 220,
    });
    setActivity('Logs loaded', 'ok');
  } catch (error) {
    setActivity(errorMessage(error), 'bad');
  } finally {
    setBusy(false);
  }
}

function openLocalAxbi() {
  if (!currentStatus || !currentStatus.web_url) {
    setActivity('Local AX-BI URL is unavailable', 'bad');
    return;
  }
  window.location.assign(currentStatus.web_url);
}

function connectToServer(event) {
  event.preventDefault();
  const value = elements.serverUrl.value.trim();
  try {
    const url = new URL(value);
    if (url.protocol !== 'http:' && url.protocol !== 'https:') {
      throw new Error('Server URL must use http or https');
    }
    if (url.username || url.password) {
      throw new Error('Server URL must not include credentials');
    }
    window.location.assign(url.toString());
  } catch (error) {
    setActivity(errorMessage(error), 'bad');
  }
}

function wireEvents() {
  elements.refresh.addEventListener('click', () => {
    refreshStatus('Refreshing status').catch(error => {
      setActivity(errorMessage(error), 'bad');
    });
  });
  elements.prepare.addEventListener('click', () => {
    runAction('Preparing local runtime', 'prepare_local_runtime');
  });
  elements.start.addEventListener('click', () => {
    runAction('Starting local AX-BI', 'start_local_runtime', pollUntilHealthy);
  });
  elements.stop.addEventListener('click', () => {
    runAction('Stopping local AX-BI', 'stop_local_runtime');
  });
  elements.restart.addEventListener('click', () => {
    runAction('Restarting local AX-BI', 'restart_local_runtime', pollUntilHealthy);
  });
  elements.update.addEventListener('click', () => {
    runAction('Updating local AX-BI images', 'update_local_runtime', pollUntilHealthy);
  });
  elements.credentials.addEventListener('click', showCredentials);
  elements.openLocal.addEventListener('click', openLocalAxbi);
  elements.loadLogs.addEventListener('click', loadLogs);
  document.getElementById('connectForm').addEventListener('submit', connectToServer);
}

wireEvents();
refreshStatus('Checking local runtime').catch(error => {
  setActivity(errorMessage(error), 'bad');
});
