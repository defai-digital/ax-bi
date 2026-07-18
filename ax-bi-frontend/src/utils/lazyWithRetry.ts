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
import { ComponentType, lazy, LazyExoticComponent } from 'react';

export const CHUNK_LOAD_RELOAD_KEY = 'axbi_chunk_load_reload';

export function isChunkLoadError(error: unknown): boolean {
  if (!error || typeof error !== 'object') {
    return false;
  }
  const err = error as { name?: string; message?: string };
  const message = err.message || '';
  return (
    err.name === 'ChunkLoadError' ||
    /Loading chunk [\w-]+ failed/i.test(message) ||
    /Failed to fetch dynamically imported module/i.test(message)
  );
}

/** @returns true if a reload was scheduled */
export function recoverFromChunkLoadError(error: unknown): boolean {
  if (!isChunkLoadError(error) || typeof window === 'undefined') {
    return false;
  }
  let alreadyReloaded = false;
  try {
    alreadyReloaded =
      window.sessionStorage.getItem(CHUNK_LOAD_RELOAD_KEY) === '1';
  } catch {
    alreadyReloaded = false;
  }
  if (alreadyReloaded) {
    return false;
  }
  try {
    window.sessionStorage.setItem(CHUNK_LOAD_RELOAD_KEY, '1');
  } catch {
    // ignore storage failures
  }
  window.location.reload();
  return true;
}

/**
 * React.lazy wrapper that recovers from webpack ChunkLoadError.
 *
 * After a dev-server recompile (or a new deploy), the shell may still
 * reference an old content-hashed chunk. One forced reload fetches a
 * fresh shell/manifest; a second failure surfaces the original error so
 * we do not loop forever.
 */
export function lazyWithRetry<T extends ComponentType<any>>(
  factory: () => Promise<{ default: T }>,
): LazyExoticComponent<T> {
  return lazy(async () => {
    try {
      const mod = await factory();
      try {
        window.sessionStorage.removeItem(CHUNK_LOAD_RELOAD_KEY);
      } catch {
        // sessionStorage may be unavailable (private mode / embedded)
      }
      return mod;
    } catch (error) {
      if (recoverFromChunkLoadError(error)) {
        // Keep the lazy promise pending while the page reloads.
        return new Promise(() => {});
      }
      throw error;
    }
  });
}

export default lazyWithRetry;
