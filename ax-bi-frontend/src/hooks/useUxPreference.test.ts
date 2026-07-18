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

import { act, renderHook, waitFor } from '@testing-library/react';
import { AxBIClient } from '@ax-bi/ui-core';
import {
  resetUxPreferencesCache,
  useUxPreference,
} from 'src/hooks/useUxPreference';
import getBootstrapData from 'src/utils/getBootstrapData';

jest.mock('@ax-bi/ui-core', () => ({
  ...jest.requireActual('@ax-bi/ui-core'),
  AxBIClient: {
    get: jest.fn(),
    put: jest.fn(),
  },
}));

jest.mock('src/utils/getBootstrapData', () => ({
  __esModule: true,
  default: jest.fn(() => ({})),
}));

const mockGet = AxBIClient.get as jest.Mock;
const mockPut = AxBIClient.put as jest.Mock;
const mockBootstrapData = getBootstrapData as jest.Mock;

const ENDPOINT = '/api/v1/me/preferences/';

beforeEach(() => {
  jest.clearAllMocks();
  localStorage.clear();
  resetUxPreferencesCache();
  mockPut.mockResolvedValue({ json: { result: {} } });
  mockBootstrapData.mockReturnValue({ user: { userId: 1 } });
});

test('returns the default value when nothing is stored anywhere', async () => {
  mockGet.mockResolvedValue({ json: { result: {} } });

  const { result } = renderHook(() => useUxPreference('ux.test.flag', false));

  expect(result.current[0]).toBe(false);
  await waitFor(() =>
    expect(mockGet).toHaveBeenCalledWith({ endpoint: ENDPOINT }),
  );
  expect(result.current[0]).toBe(false);
});

test('adopts the server value once preferences load', async () => {
  mockGet.mockResolvedValue({ json: { result: { 'ux.test.flag': true } } });

  const { result } = renderHook(() => useUxPreference('ux.test.flag', false));

  await waitFor(() => expect(result.current[0]).toBe(true));
});

test('falls back to localStorage when the request fails', async () => {
  mockGet.mockRejectedValue(new Error('401'));
  localStorage.setItem('ux.test.flag', 'true');

  const { result } = renderHook(() => useUxPreference('ux.test.flag', false));

  await waitFor(() => expect(mockGet).toHaveBeenCalled());
  expect(result.current[0]).toBe(true);
});

test('falls back to the default when the request fails and localStorage is empty', async () => {
  mockGet.mockRejectedValue(new Error('offline'));

  const { result } = renderHook(() => useUxPreference('ux.test.mode', 'card'));

  await waitFor(() => expect(mockGet).toHaveBeenCalled());
  expect(result.current[0]).toBe('card');
});

test('server value wins over the localStorage fallback', async () => {
  mockGet.mockResolvedValue({ json: { result: { 'ux.test.flag': false } } });
  localStorage.setItem('ux.test.flag', 'true');

  const { result } = renderHook(() => useUxPreference('ux.test.flag', true));

  await waitFor(() => expect(result.current[0]).toBe(false));
});

test('setter updates optimistically, mirrors to localStorage, and PUTs', async () => {
  mockGet.mockResolvedValue({ json: { result: {} } });

  const { result } = renderHook(() =>
    useUxPreference<boolean>('ux.test.flag', false),
  );
  await waitFor(() => expect(mockGet).toHaveBeenCalled());

  act(() => {
    result.current[1](true);
  });

  expect(result.current[0]).toBe(true);
  expect(localStorage.getItem('ux.test.flag')).toBe('true');
  expect(mockPut).toHaveBeenCalledWith({
    endpoint: ENDPOINT,
    body: JSON.stringify({ 'ux.test.flag': true }),
    headers: { 'Content-Type': 'application/json' },
  });
});

test('setter still updates locally when the PUT fails', async () => {
  mockGet.mockResolvedValue({ json: { result: {} } });
  mockPut.mockRejectedValue(new Error('offline'));

  const { result } = renderHook(() =>
    useUxPreference<boolean>('ux.test.flag', false),
  );
  await waitFor(() => expect(mockGet).toHaveBeenCalled());

  act(() => {
    result.current[1](true);
  });

  expect(result.current[0]).toBe(true);
  expect(localStorage.getItem('ux.test.flag')).toBe('true');
});

test('writes through a legacy localStorage value the server is missing', async () => {
  mockGet.mockResolvedValue({ json: { result: {} } });
  localStorage.setItem('home__onboarding_checklist_dismissed', '1');

  const { result } = renderHook(() =>
    useUxPreference('ux.home.onboarding_dismissed', false, {
      localStorageKey: 'home__onboarding_checklist_dismissed',
      readLegacy: raw => (raw === 1 ? true : undefined),
    }),
  );

  expect(result.current[0]).toBe(true);
  await waitFor(() =>
    expect(mockPut).toHaveBeenCalledWith({
      endpoint: ENDPOINT,
      body: JSON.stringify({ 'ux.home.onboarding_dismissed': true }),
      headers: { 'Content-Type': 'application/json' },
    }),
  );
});

test('does not write through when the server already has the key', async () => {
  mockGet.mockResolvedValue({
    json: { result: { 'ux.home.onboarding_dismissed': false } },
  });
  localStorage.setItem('home__onboarding_checklist_dismissed', '1');

  const { result } = renderHook(() =>
    useUxPreference('ux.home.onboarding_dismissed', true, {
      localStorageKey: 'home__onboarding_checklist_dismissed',
      readLegacy: raw => (raw === 1 ? true : undefined),
    }),
  );

  await waitFor(() => expect(mockGet).toHaveBeenCalled());
  expect(result.current[0]).toBe(false);
  expect(mockPut).not.toHaveBeenCalled();
});

test('reads a legacy object-shaped value via readLegacy', async () => {
  mockGet.mockResolvedValue({ json: { result: {} } });
  localStorage.setItem('5', JSON.stringify({ thumbnails: false }));

  const { result } = renderHook(() =>
    useUxPreference('ux.home.thumbnails', true, {
      localStorageKey: '5',
      readLegacy: raw =>
        raw != null && typeof raw === 'object'
          ? (raw as { thumbnails?: boolean }).thumbnails
          : undefined,
    }),
  );

  expect(result.current[0]).toBe(false);
  await waitFor(() =>
    expect(mockPut).toHaveBeenCalledWith({
      endpoint: ENDPOINT,
      body: JSON.stringify({ 'ux.home.thumbnails': false }),
      headers: { 'Content-Type': 'application/json' },
    }),
  );
});

test('shares one server document across hook instances', async () => {
  mockGet.mockResolvedValue({ json: { result: { 'ux.test.flag': true } } });

  const first = renderHook(() => useUxPreference('ux.test.flag', false));
  const second = renderHook(() => useUxPreference('ux.test.other', 'a'));

  await waitFor(() => expect(first.result.current[0]).toBe(true));
  expect(mockGet).toHaveBeenCalledTimes(1);

  act(() => {
    first.result.current[1](false);
  });
  expect(second.result.current[0]).toBe('a');
});

test('re-anchors the shared cache when the bootstrap user changes', async () => {
  mockBootstrapData.mockReturnValue({ user: { userId: 1 } });
  mockGet.mockResolvedValue({ json: { result: { 'ux.test.flag': true } } });

  const { result, rerender } = renderHook(() =>
    useUxPreference('ux.test.flag', false),
  );
  await waitFor(() => expect(result.current[0]).toBe(true));
  expect(mockGet).toHaveBeenCalledTimes(1);

  // A different user signs in within the same page session: the cached
  // document must be dropped and refetched instead of leaking user 1's
  // preferences into user 2's UI.
  mockBootstrapData.mockReturnValue({ user: { userId: 2 } });
  mockGet.mockResolvedValue({ json: { result: { 'ux.test.flag': false } } });
  rerender();

  await waitFor(() => expect(result.current[0]).toBe(false));
  expect(mockGet).toHaveBeenCalledTimes(2);
});
