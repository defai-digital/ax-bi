/**
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
import {
  ensureIsArray,
  isFeatureEnabled,
  FeatureFlag,
  makeApi,
  AxBIClient,
  getClientErrorObject,
  parseErrorJson,
  AxBIError,
} from '@ax-bi/ui-core';
import { logging } from '@ax-bi/core/utils';
import getBootstrapData from 'src/utils/getBootstrapData';

type AsyncEvent = {
  id?: string | null;
  channel_id: string;
  job_id: string;
  user_id?: string;
  status: string;
  errors?: AxBIError[];
  result_url: string | null;
};

type CachedDataResponse = {
  status: string;
  data: any;
};
type AppConfig = Record<string, any>;
type ListenerFn = (asyncEvent: AsyncEvent) => Promise<any>;

const TRANSPORT_POLLING = 'polling';
const TRANSPORT_WS = 'ws';
const JOB_STATUS = {
  PENDING: 'pending',
  RUNNING: 'running',
  ERROR: 'error',
  DONE: 'done',
};
const LOCALSTORAGE_KEY = 'last_async_event_id';
const POLLING_URL = '/api/v1/async_event/';
const MAX_RETRIES = 6;
const RETRY_DELAY = 100;
// Default max wait for an async job before rejecting (5 minutes).
const DEFAULT_MAX_WAIT_MS = 5 * 60 * 1000;

let config: AppConfig;
let transport: string;
let pollingDelayMs: number;
let maxWaitMs: number;
let pollingTimeoutId: number;
let listenersByJobId: Map<string, ListenerFn>;
let retriesByJobId: Map<string, number>;
let lastReceivedEventId: string | null | undefined;

const addListener = (id: string, fn: ListenerFn) => {
  listenersByJobId.set(id, fn);
};

const removeListener = (id: string) => {
  if (!listenersByJobId.has(id)) return;
  listenersByJobId.delete(id);
};

const fetchCachedData = async (
  asyncEvent: AsyncEvent,
): Promise<CachedDataResponse> => {
  let status = 'success';
  let data;
  try {
    const { json } = await AxBIClient.get({
      endpoint: String(asyncEvent.result_url),
    });
    data = 'result' in json ? json.result : json;
  } catch (response) {
    status = 'error';
    data = await getClientErrorObject(response);
  }

  return { status, data };
};

export const waitForAsyncData = async (asyncResponse: AsyncEvent) =>
  new Promise((resolve, reject) => {
    const jobId = asyncResponse.job_id;
    let settled = false;

    const timeoutId = window.setTimeout(() => {
      if (settled) return;
      settled = true;
      removeListener(jobId);
      reject(
        new Error(
          `Async event timed out after ${maxWaitMs ?? DEFAULT_MAX_WAIT_MS}ms for job_id ${jobId}`,
        ),
      );
    }, maxWaitMs ?? DEFAULT_MAX_WAIT_MS);

    const settle = (fn: (value: any) => void, value: any) => {
      if (settled) return;
      settled = true;
      window.clearTimeout(timeoutId);
      removeListener(jobId);
      fn(value);
    };

    const listener = async (asyncEvent: AsyncEvent) => {
      switch (asyncEvent.status) {
        case JOB_STATUS.DONE: {
          let { data, status } = await fetchCachedData(asyncEvent); // eslint-disable-line prefer-const
          data = ensureIsArray(data);
          if (status === 'success') {
            settle(resolve, data);
          } else {
            settle(reject, data);
          }
          break;
        }
        case JOB_STATUS.ERROR: {
          const err = parseErrorJson(asyncEvent);
          settle(reject, err);
          break;
        }
        default: {
          logging.warn('received event with status', asyncEvent.status);
        }
      }
    };
    addListener(jobId, listener);
  });

const fetchEvents = makeApi<
  { last_id?: string | null },
  { result: AsyncEvent[] }
>({
  method: 'GET',
  endpoint: POLLING_URL,
});

const setLastId = (asyncEvent: AsyncEvent) => {
  lastReceivedEventId = asyncEvent.id;
  try {
    localStorage.setItem(LOCALSTORAGE_KEY, lastReceivedEventId as string);
  } catch (err) {
    logging.warn('Error saving event Id to localStorage', err);
  }
};

export const processEvents = async (events: AsyncEvent[]) => {
  events.forEach((asyncEvent: AsyncEvent) => {
    const jobId = asyncEvent.job_id;
    const listener = listenersByJobId.get(jobId);
    // `jobId` originates from server/WebSocket payloads, so the listener is
    // resolved exclusively through a Map (never plain-object property access,
    // which would expose the prototype chain), and we confirm the retrieved
    // value is a registered function before dispatching the event to it.
    if (typeof listener === 'function') {
      listener(asyncEvent);
      retriesByJobId.delete(jobId);
    } else {
      // handle race condition where event is received
      // before listener is registered
      const retries = (retriesByJobId.get(jobId) ?? 0) + 1;
      retriesByJobId.set(jobId, retries);

      if (retries <= MAX_RETRIES) {
        setTimeout(() => {
          processEvents([asyncEvent]);
        }, RETRY_DELAY * retries);
      } else {
        retriesByJobId.delete(jobId);
        logging.warn('listener not found for job_id', asyncEvent.job_id);
      }
    }
    setLastId(asyncEvent);
  });
};

const loadEventsFromApi = async () => {
  const eventArgs = lastReceivedEventId ? { last_id: lastReceivedEventId } : {};
  if (listenersByJobId.size) {
    try {
      const { result: events } = await fetchEvents(eventArgs);
      if (events?.length) await processEvents(events);
    } catch (err) {
      logging.warn(err);
    }
  }

  if (transport === TRANSPORT_POLLING) {
    pollingTimeoutId = window.setTimeout(loadEventsFromApi, pollingDelayMs);
  }
};

const wsConnectMaxRetries = 6;
const wsConnectErrorDelay = 2500;
let wsConnectRetries = 0;
let wsConnectTimeout: any;
let ws: WebSocket | null = null;
// Bumped on every connect/close so stale close handlers never reconnect.
let wsGeneration = 0;

const closeWebSocket = (): void => {
  if (wsConnectTimeout) {
    clearTimeout(wsConnectTimeout);
    wsConnectTimeout = undefined;
  }
  wsGeneration += 1;
  if (ws) {
    const socket = ws;
    ws = null;
    try {
      if (socket.readyState < 2) {
        socket.close();
      }
    } catch (err) {
      logging.warn('Error closing WebSocket', err);
    }
  }
  wsConnectRetries = 0;
};

const wsConnect = (): void => {
  // Ensure any previous socket is fully torn down before opening a new one.
  closeWebSocket();

  let url = config.GLOBAL_ASYNC_QUERIES_WEBSOCKET_URL;
  if (lastReceivedEventId) url += `?last_id=${lastReceivedEventId}`;
  const generation = wsGeneration;
  const socket = new WebSocket(url);
  ws = socket;

  socket.addEventListener('open', () => {
    if (generation !== wsGeneration || ws !== socket) return;
    logging.log('WebSocket connected');
    clearTimeout(wsConnectTimeout);
    wsConnectRetries = 0;
  });

  socket.addEventListener('close', () => {
    // Only reconnect if this is still the active generation (not closed by re-init).
    if (generation !== wsGeneration || ws !== socket) return;
    wsConnectTimeout = setTimeout(() => {
      if (generation !== wsGeneration) return;
      wsConnectRetries += 1;
      if (wsConnectRetries <= wsConnectMaxRetries) {
        wsConnect();
      } else {
        logging.warn('WebSocket not available, falling back to async polling');
        loadEventsFromApi();
      }
    }, wsConnectErrorDelay);
  });

  socket.addEventListener('error', () => {
    if (generation !== wsGeneration || ws !== socket) return;
    // https://developer.mozilla.org/en-US/docs/Web/API/WebSocket/readyState
    if (socket.readyState < 2) socket.close();
  });

  socket.addEventListener('message', async event => {
    if (generation !== wsGeneration || ws !== socket) return;
    let events: AsyncEvent[] = [];
    try {
      events = [JSON.parse(event.data)];
      await processEvents(events);
    } catch (err) {
      logging.warn(err);
    }
  });
};

export const init = (appConfig?: AppConfig) => {
  if (!isFeatureEnabled(FeatureFlag.GlobalAsyncQueries)) return;
  if (pollingTimeoutId) clearTimeout(pollingTimeoutId);
  // Tear down any existing WS before re-initializing (avoids leaking sockets).
  closeWebSocket();

  listenersByJobId = new Map();
  retriesByJobId = new Map();
  lastReceivedEventId = null;

  config = appConfig || getBootstrapData().common.conf;
  transport = config.GLOBAL_ASYNC_QUERIES_TRANSPORT || TRANSPORT_POLLING;
  pollingDelayMs = config.GLOBAL_ASYNC_QUERIES_POLLING_DELAY || 500;
  maxWaitMs =
    config.GLOBAL_ASYNC_QUERIES_MAX_WAIT_MS || DEFAULT_MAX_WAIT_MS;

  try {
    lastReceivedEventId = localStorage.getItem(LOCALSTORAGE_KEY);
  } catch (err) {
    logging.warn('Failed to fetch last event Id from localStorage');
  }

  if (transport === TRANSPORT_POLLING) {
    loadEventsFromApi();
  }
  if (transport === TRANSPORT_WS) {
    wsConnect();
  }
};

init();
