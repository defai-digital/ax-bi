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

import { normalizeHttpBaseUrl, stripTrailingSlashes } from './url.js';

test('stripTrailingSlashes removes only trailing slash characters', () => {
  expect(stripTrailingSlashes('https://example.test/ax-bi///')).toBe(
    'https://example.test/ax-bi',
  );
  expect(stripTrailingSlashes('https://example.test/ax-bi/path')).toBe(
    'https://example.test/ax-bi/path',
  );
});

test('normalizeHttpBaseUrl canonicalizes HTTP service bases', () => {
  expect(normalizeHttpBaseUrl(' http://localhost:8088/ ')).toBe(
    'http://localhost:8088',
  );
  expect(normalizeHttpBaseUrl('https://example.test/ax-bi///')).toBe(
    'https://example.test/ax-bi',
  );
});

test('normalizeHttpBaseUrl rejects invalid service bases', () => {
  expect(() => normalizeHttpBaseUrl('not a url', 'baseUrl')).toThrow(
    'baseUrl must be a valid HTTP(S) URL',
  );
  expect(() => normalizeHttpBaseUrl('ftp://example.test', 'baseUrl')).toThrow(
    'baseUrl must use HTTP or HTTPS',
  );
  expect(() =>
    normalizeHttpBaseUrl('https://user:pass@example.test', 'baseUrl'),
  ).toThrow('baseUrl must not include credentials');
  expect(() =>
    normalizeHttpBaseUrl('https://example.test?token=abc', 'baseUrl'),
  ).toThrow('baseUrl must not include query or fragment');
  expect(() =>
    normalizeHttpBaseUrl('https://example.test#fragment', 'baseUrl'),
  ).toThrow('baseUrl must not include query or fragment');
});
