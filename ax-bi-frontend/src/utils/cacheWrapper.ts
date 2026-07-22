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

/**
 * Wraps a function with an in-memory cache keyed by its arguments.
 *
 * When the wrapped function returns a Promise that rejects, the cache entry is
 * deleted so the next call retries instead of permanently caching the failure.
 */
export const cacheWrapper =
  <T extends Array<any>, U>(
    fn: (...args: T) => U,
    cache: Map<string, any>,
    keyFn: (...args: T) => string = (...args: T) => JSON.stringify([...args]),
  ) =>
  (...args: T): U => {
    const key = keyFn(...args);
    if (cache.has(key)) {
      return cache.get(key);
    }
    const result = fn(...args);
    cache.set(key, result);
    // Drop rejected promises so subsequent callers can retry.
    if (result != null && typeof (result as any).then === 'function') {
      (result as unknown as Promise<unknown>).catch(() => {
        if (cache.get(key) === result) {
          cache.delete(key);
        }
      });
    }
    return result;
  };
