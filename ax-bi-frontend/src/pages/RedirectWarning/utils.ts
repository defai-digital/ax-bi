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

const ALLOWED_SCHEMES = ['http:', 'https:'];

/**
 * Return true if the URL scheme is safe for navigation.
 * Blocks javascript:, data:, vbscript:, file:, etc.
 */
export function isAllowedScheme(url: string): boolean {
  try {
    const parsed = new URL(url, window.location.origin);
    return ALLOWED_SCHEMES.includes(parsed.protocol);
  } catch {
    return false;
  }
}

/**
 * Read the target URL from the current page's query string.
 *
 * URLSearchParams.get() already percent-decodes the value, so we must NOT
 * call decodeURIComponent again (doing so would allow double-encoded
 * payloads like `javascript%253Aalert(1)` to bypass scheme checks).
 */
export function getTargetUrl(): string {
  const params = new URLSearchParams(window.location.search);
  const url = params.get('url') ?? '';
  return url.trim();
}

export function getSafeTargetUrl(): string | null {
  const targetUrl = getTargetUrl();
  if (!targetUrl || !isAllowedScheme(targetUrl)) {
    return null;
  }

  try {
    return new URL(targetUrl, window.location.origin).href;
  } catch {
    return null;
  }
}
