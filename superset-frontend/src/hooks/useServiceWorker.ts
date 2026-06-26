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
import { useState, useEffect, useCallback } from 'react';

export interface ServiceWorkerState {
  /** Whether the service worker is registered and active */
  isRegistered: boolean;
  /** Whether a new update is available and waiting */
  isUpdateAvailable: boolean;
  /** Whether the service worker is currently installing */
  isInstalling: boolean;
  /** The waiting service worker, if any */
  waitingWorker: ServiceWorker | null;
  /** Apply the pending update (skips waiting) */
  applyUpdate: () => void;
  /** Clear the service worker cache */
  clearCache: () => void;
}

/**
 * Hook to manage service worker registration and updates
 */
export function useServiceWorker(): ServiceWorkerState {
  const [isRegistered, setIsRegistered] = useState(false);
  const [isUpdateAvailable, setIsUpdateAvailable] = useState(false);
  const [isInstalling, setIsInstalling] = useState(false);
  const [waitingWorker, setWaitingWorker] = useState<ServiceWorker | null>(
    null,
  );

  useEffect(() => {
    if (!('serviceWorker' in navigator)) {
      return undefined;
    }

    // A service worker that caches content-hashed webpack chunks is safe in
    // production (filenames are immutable) but breaks the dev server: it serves
    // stale chunks and fights HMR, producing ChunkLoadError timeouts. Skip
    // registration in development, and actively tear down any worker/caches a
    // previous session left behind so an already-affected dev session recovers.
    if (process.env.WEBPACK_MODE === 'development') {
      navigator.serviceWorker
        .getRegistrations()
        .then(registrations =>
          Promise.all(registrations.map(reg => reg.unregister())),
        )
        .catch(() => {});
      if ('caches' in window) {
        caches
          .keys()
          .then(keys => Promise.all(keys.map(key => caches.delete(key))))
          .catch(() => {});
      }
      return undefined;
    }

    let registration: ServiceWorkerRegistration;
    let updateIntervalId: ReturnType<typeof setInterval> | undefined;

    const handleUpdate = () => {
      if (!registration) return;

      const { installing } = registration;
      const { waiting } = registration;

      if (installing) {
        setIsInstalling(true);

        installing.addEventListener('statechange', () => {
          if (installing.state === 'installed') {
            setIsInstalling(false);
            if (navigator.serviceWorker.controller) {
              // New update available
              setIsUpdateAvailable(true);
              setWaitingWorker(installing);
            }
          }
        });
      }

      if (waiting) {
        setIsUpdateAvailable(true);
        setWaitingWorker(waiting);
      }
    };

    const registerServiceWorker = async () => {
      try {
        registration = await navigator.serviceWorker.register(
          '/static/service-worker.js',
          {
            scope: '/',
          },
        );

        setIsRegistered(true);

        // Check for updates periodically (every hour)
        const UPDATE_CHECK_INTERVAL = 60 * 60 * 1000;
        updateIntervalId = setInterval(() => {
          registration.update();
        }, UPDATE_CHECK_INTERVAL);

        // Listen for new service workers
        registration.addEventListener('updatefound', handleUpdate);

        // Check if there's already a waiting worker
        if (registration.waiting) {
          handleUpdate();
        }

        // Listen for controller change (new SW activated)
        navigator.serviceWorker.addEventListener('controllerchange', () => {
          // Reload to get the new version
          window.location.reload();
        });

        // Listen for messages from service worker
        navigator.serviceWorker.addEventListener('message', event => {
          if (event.data?.type === 'CACHE_CLEARED') {
            // Cache was cleared, could show notification
            console.log('Service worker cache cleared');
          }
        });
      } catch (error) {
        console.error('Service worker registration failed:', error);
      }
    };

    // Register after page load to avoid blocking rendering
    if (document.readyState === 'complete') {
      registerServiceWorker();
    } else {
      window.addEventListener('load', registerServiceWorker);
    }

    return () => {
      if (updateIntervalId !== undefined) {
        clearInterval(updateIntervalId);
      }
      if (registration) {
        registration.removeEventListener('updatefound', handleUpdate);
      }
    };
  }, []);

  const applyUpdate = useCallback(() => {
    if (waitingWorker) {
      // Tell the waiting service worker to skip waiting
      waitingWorker.postMessage({ type: 'SKIP_WAITING' });
      setIsUpdateAvailable(false);
      setWaitingWorker(null);
    }
  }, [waitingWorker]);

  const clearCache = useCallback(() => {
    if (navigator.serviceWorker.controller) {
      navigator.serviceWorker.controller.postMessage({ type: 'CLEAR_CACHE' });
    }
  }, []);

  return {
    isRegistered,
    isUpdateAvailable,
    isInstalling,
    waitingWorker,
    applyUpdate,
    clearCache,
  };
}

export default useServiceWorker;
