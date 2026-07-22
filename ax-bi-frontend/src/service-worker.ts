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

interface ServiceWorkerExtendableEvent {
  waitUntil(promise: Promise<unknown>): void;
}

interface ServiceWorkerFetchEvent extends ServiceWorkerExtendableEvent {
  request: Request;
  respondWith(response: Response | Promise<Response>): void;
}

interface ServiceWorkerMessageEvent extends ServiceWorkerExtendableEvent {
  data?: {
    type?: string;
  };
  source?: {
    postMessage(message: unknown): void;
  } | null;
}

interface ServiceWorkerGlobal {
  location: Location;
  clients: {
    claim(): Promise<void>;
  };
  skipWaiting(): Promise<void>;
  addEventListener(
    type: 'install' | 'activate',
    listener: (event: ServiceWorkerExtendableEvent) => void,
  ): void;
  addEventListener(
    type: 'fetch',
    listener: (event: ServiceWorkerFetchEvent) => void,
  ): void;
  addEventListener(
    type: 'message',
    listener: (event: ServiceWorkerMessageEvent) => void,
  ): void;
}

// Service Worker types are declared locally because the frontend tsconfig does
// not include the WebWorker lib.
declare const self: ServiceWorkerGlobal;

// Cache configuration
const CACHE_VERSION = 'axbi-cache-v1';
const STATIC_CACHE = `static-${CACHE_VERSION}`;

// Cache limits
const MAX_STATIC_ENTRIES = 100;

// Static assets to precache (will be populated by webpack)
const PRECACHE_URLS: string[] = [];

// Patterns for different caching strategies
const STATIC_ASSET_PATTERNS = [
  /\.(?:js|css|woff2?|ttf|otf|eot)$/,
  /\.(?:png|jpg|jpeg|gif|svg|ico|webp)$/,
];

const API_PATTERNS = [
  /\/api\/v1\//,
];

// Routes that should never be cached
const NO_CACHE_PATTERNS = [
  /\/login\//,
  /\/logout\//,
  /\/api\/v1\/security\//,
  /\/health$/,
];

/**
 * Check if a URL matches any of the given patterns
 */
function matchesPatterns(url: string, patterns: RegExp[]): boolean {
  return patterns.some(pattern => pattern.test(url));
}

/**
 * Trim cache to max entries (FIFO)
 */
async function trimCache(cacheName: string, maxEntries: number): Promise<void> {
  const cache = await caches.open(cacheName);
  const keys = await cache.keys();

  if (keys.length > maxEntries) {
    // Delete oldest entries
    const deleteCount = keys.length - maxEntries;
    for (let i = 0; i < deleteCount; i += 1) {
      await cache.delete(keys[i]);
    }
  }
}

/**
 * Stale-while-revalidate strategy for static assets
 * Returns cached response immediately, then updates cache in background
 */
async function staleWhileRevalidate(
  request: Request,
  cacheName: string,
  maxEntries: number,
): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cachedResponse = await cache.match(request);

  // Fetch fresh response
  const fetchPromise: Promise<Response> = fetch(request)
    .then(response => {
      // Only cache successful responses
      if (response.ok) {
        cache.put(request, response.clone());
        trimCache(cacheName, maxEntries);
      }
      return response;
    })
    .catch(
      () =>
        cachedResponse ??
        new Response('', {
          status: 503,
          statusText: 'Service Unavailable',
        }),
    );

  // Return cache hit immediately, or wait for fetch if no cache
  return cachedResponse || fetchPromise;
}

/**
 * Network-only strategy for API and navigation requests.
 *
 * - API: runtime metadata changes after uploads/saves; cache would be stale.
 * - HTML navigations: authenticated pages embed user bootstrap JSON, so they
 *   must never be served from cache (would leak another user's shell).
 */
async function networkOnly(request: Request): Promise<Response> {
  try {
    return await fetch(request);
  } catch {
    // Prefer JSON body for API-shaped requests; plain 503 for navigations.
    const acceptsJson = request.headers.get('accept')?.includes('application/json');
    if (acceptsJson || matchesPatterns(new URL(request.url).pathname, API_PATTERNS)) {
      return new Response(JSON.stringify({ error: 'Network error' }), {
        status: 503,
        statusText: 'Service Unavailable',
        headers: { 'Content-Type': 'application/json' },
      });
    }
    return new Response('', {
      status: 503,
      statusText: 'Service Unavailable',
    });
  }
}

/**
 * Clean up old cache versions
 */
async function cleanupOldCaches(): Promise<void> {
  const cacheNames = await caches.keys();
  const currentCaches = [STATIC_CACHE];

  await Promise.all(
    cacheNames
      .filter(name => !currentCaches.includes(name))
      .map(name => caches.delete(name)),
  );
}

// Install event - precache essential assets
self.addEventListener('install', event => {
  event.waitUntil(
    caches
      .open(STATIC_CACHE)
      .then(cache => {
        if (PRECACHE_URLS.length > 0) {
          return cache.addAll(PRECACHE_URLS);
        }
        return Promise.resolve();
      })
      .then(() => self.skipWaiting()),
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(cleanupOldCaches().then(() => self.clients.claim()));
});

// Fetch event - handle requests with appropriate caching strategy
self.addEventListener('fetch', event => {
  const { request } = event;
  const url = new URL(request.url);

  // Only handle same-origin requests
  if (url.origin !== self.location.origin) {
    return;
  }

  // Skip non-GET requests (except for API calls we might want to cache)
  if (request.method !== 'GET') {
    return;
  }

  // Never cache auth and health endpoints
  if (matchesPatterns(url.pathname, NO_CACHE_PATTERNS)) {
    return;
  }

  // HTML navigation requests: network-only. Authenticated pages embed
  // user bootstrap JSON; caching them (even network-first with a long
  // maxAge) risks serving another user's session shell offline/stale.
  if (
    request.mode === 'navigate' ||
    request.headers.get('accept')?.includes('text/html')
  ) {
    event.respondWith(networkOnly(request));
    return;
  }

  // Static assets - stale while revalidate
  if (matchesPatterns(url.pathname, STATIC_ASSET_PATTERNS)) {
    event.respondWith(
      staleWhileRevalidate(request, STATIC_CACHE, MAX_STATIC_ENTRIES),
    );
    return;
  }

  // API requests - network only to avoid stale metadata after uploads
  if (matchesPatterns(url.pathname, API_PATTERNS)) {
    event.respondWith(networkOnly(request));
    return;
  }

  // Default - network only
});

// Message event - handle messages from clients
self.addEventListener('message', event => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting();
  }

  if (event.data?.type === 'CLEAR_CACHE') {
    event.waitUntil(
      caches
        .keys()
        .then(names => Promise.all(names.map(name => caches.delete(name))))
        .then(() => {
          // Notify client that cache is cleared
          event.source?.postMessage({ type: 'CACHE_CLEARED' });
        }),
    );
  }
});

export {};
