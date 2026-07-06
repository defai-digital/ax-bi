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

import { isAllowedScheme, getTargetUrl, getSafeTargetUrl } from './utils';

test('isAllowedScheme accepts http URLs', () => {
  expect(isAllowedScheme('http://example.com')).toBe(true);
});

test('isAllowedScheme accepts https URLs', () => {
  expect(isAllowedScheme('https://example.com/page?q=1')).toBe(true);
});

test('isAllowedScheme blocks javascript: URLs', () => {
  // oxlint-disable-next-line no-script-url -- testing that dangerous schemes are blocked
  expect(isAllowedScheme('javascript:alert(1)')).toBe(false);
});

test('isAllowedScheme blocks data: URLs', () => {
  expect(isAllowedScheme('data:text/html,<script>alert(1)</script>')).toBe(
    false,
  );
});

test('isAllowedScheme blocks vbscript: URLs', () => {
  expect(isAllowedScheme('vbscript:MsgBox("XSS")')).toBe(false);
});

test('isAllowedScheme blocks file: URLs', () => {
  expect(isAllowedScheme('file:///etc/passwd')).toBe(false);
});

test('isAllowedScheme allows relative URLs', () => {
  expect(isAllowedScheme('/dashboard/1')).toBe(true);
});

test('getTargetUrl reads the url query parameter', () => {
  const locationSpy = jest.spyOn(window, 'location', 'get').mockReturnValue({
    search: '?url=https%3A%2F%2Fexample.com%2Fpage',
  } as Location);
  expect(getTargetUrl()).toBe('https://example.com/page');
  locationSpy.mockRestore();
});

test('getTargetUrl returns empty string when url param is missing', () => {
  const locationSpy = jest
    .spyOn(window, 'location', 'get')
    .mockReturnValue({ search: '' } as Location);
  expect(getTargetUrl()).toBe('');
  locationSpy.mockRestore();
});

test('getTargetUrl does not double-decode percent-encoded values', () => {
  // %253A is the double-encoding of ":" — after one decode it should remain %3A
  const locationSpy = jest
    .spyOn(window, 'location', 'get')
    .mockReturnValue({ search: '?url=javascript%253Aalert(1)' } as Location);
  expect(getTargetUrl()).toBe('javascript%3Aalert(1)');
  locationSpy.mockRestore();
});

test('getSafeTargetUrl returns a normalized http URL', () => {
  const locationSpy = jest.spyOn(window, 'location', 'get').mockReturnValue({
    origin: 'https://superset.example',
    search: '?url=https%3A%2F%2Fexample.com%2Fpage',
  } as Location);
  expect(getSafeTargetUrl()).toBe('https://example.com/page');
  locationSpy.mockRestore();
});

test('getSafeTargetUrl returns null for dangerous schemes', () => {
  const locationSpy = jest.spyOn(window, 'location', 'get').mockReturnValue({
    origin: 'https://superset.example',
    search: '?url=javascript%3Aalert(1)',
  } as Location);
  expect(getSafeTargetUrl()).toBeNull();
  locationSpy.mockRestore();
});
