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
import { renderHook, act } from '@testing-library/react';
import { AxBIClient } from '@ax-bi/ui-core';
import { useDownloadScreenshot } from './useDownloadScreenshot';
import { DownloadScreenshotFormat } from '../components/menu/DownloadMenuItems/types';

jest.mock('@ax-bi/ui-core', () => ({
  // keep the real module surface: transitively imported modules read many
  // other exports (initFeatureFlags, formatters, registries) at module scope
  ...jest.requireActual('@ax-bi/ui-core'),
  AxBIClient: {
    post: jest.fn(),
    get: jest.fn(),
  },
  AxBIApiError: class AxBIApiError extends Error {
    status: number;
    constructor(message: string, status: number) {
      super(message);
      this.status = status;
    }
  },
}));

jest.mock('react-redux', () => ({
  ...jest.requireActual('react-redux'),
  useSelector: jest.fn(() => undefined),
}));

jest.mock('src/components/MessageToasts/withToasts', () => ({
  __esModule: true,
  // pass-through HOC: transitively imported components wrap themselves with
  // withToasts at module scope
  default: (component: unknown) => component,
  useToasts: () => ({
    addDangerToast: jest.fn(),
    addSuccessToast: jest.fn(),
    addInfoToast: jest.fn(),
  }),
}));

jest.mock('src/utils/urlUtils', () => ({
  getDashboardUrlParams: jest.fn(() => []),
}));

const RETRY_INTERVAL = 3000;
const DASHBOARD_ID = 123;
const CACHE_KEY = 'test-cache-key';

const mockPostSuccess = () =>
  (AxBIClient.post as jest.Mock).mockResolvedValue({
    json: { cache_key: CACHE_KEY },
  });

const createResponse = (): Response =>
  ({
    headers: { get: () => null },
    blob: () => Promise.resolve(new Blob(['image-data'])),
  }) as unknown as Response;

const notReadyError = () => ({ status: 404 });

// Chain several Promise.resolves to drain nested microtasks (.then/.catch/.finally
// in the hook). setImmediate-based flush would stall under fake timers.
const flushPromises = async () => {
  for (let i = 0; i < 10; i += 1) {
    // eslint-disable-next-line no-await-in-loop
    await Promise.resolve();
  }
};

const triggerDownload = async () => {
  const { result } = renderHook(() => useDownloadScreenshot(DASHBOARD_ID));
  await act(async () => {
    result.current(DownloadScreenshotFormat.PNG);
    await flushPromises();
  });
  return result;
};

beforeEach(() => {
  jest.clearAllMocks();
  // Default: GET hangs so microtask chains don't throw on undefined in tests
  // that only care about POST behavior.
  (AxBIClient.get as jest.Mock).mockReturnValue(new Promise(() => {}));
});

test('downloadScreenshot calls API with force=true to ensure fresh screenshots', async () => {
  mockPostSuccess();

  const { result } = renderHook(() => useDownloadScreenshot(DASHBOARD_ID));

  await act(async () => {
    result.current(DownloadScreenshotFormat.PNG);
  });

  expect(AxBIClient.post).toHaveBeenCalledTimes(1);
  const callArgs = (AxBIClient.post as jest.Mock).mock.calls[0][0];

  // Verify that force=true is included in the endpoint URL
  // This prevents regression where stale cached screenshots are returned
  expect(callArgs.endpoint).toContain('force');
  expect(callArgs.endpoint).toMatch(/force[:%]true|force[:%]!t/);
});

test('does not issue overlapping GETs while a previous GET is in-flight', async () => {
  jest.useFakeTimers();
  mockPostSuccess();

  // GET never resolves within the test — simulates a slow screenshot request.
  (AxBIClient.get as jest.Mock).mockImplementation(() => new Promise(() => {}));

  await triggerDownload();

  // First (immediate) GET fires right after POST resolves.
  expect(AxBIClient.get).toHaveBeenCalledTimes(1);

  // Advance past several retry intervals while the first GET is still pending.
  await act(async () => {
    jest.advanceTimersByTime(RETRY_INTERVAL * 5);
    await flushPromises();
  });

  // isFetching guard must prevent the interval from stacking new requests.
  expect(AxBIClient.get).toHaveBeenCalledTimes(1);

  jest.clearAllTimers();
  jest.useRealTimers();
});

test('triggers only one download when multiple successful responses race', async () => {
  jest.useFakeTimers();
  mockPostSuccess();

  // First GET returns 404 (not ready), then resolves 200 for every subsequent call.
  // Without the isDownloaded guard any late-arriving 200 would trigger a second click.
  (AxBIClient.get as jest.Mock)
    .mockRejectedValueOnce(notReadyError())
    .mockResolvedValue(createResponse());

  // jsdom does not implement URL.createObjectURL / revokeObjectURL — stub them.
  Object.assign(window.URL, {
    createObjectURL: jest.fn(() => 'blob:mock'),
    revokeObjectURL: jest.fn(),
  });
  const clickSpy = jest
    .spyOn(HTMLAnchorElement.prototype, 'click')
    .mockImplementation(() => {});

  await triggerDownload();

  // Drive several interval ticks so multiple 200 responses could resolve.
  await act(async () => {
    jest.advanceTimersByTime(RETRY_INTERVAL * 5);
    await flushPromises();
  });

  expect(clickSpy).toHaveBeenCalledTimes(1);

  clickSpy.mockRestore();
  jest.clearAllTimers();
  jest.useRealTimers();
});

test('non-404 GET failures still advance the retry counter', async () => {
  jest.useFakeTimers();
  mockPostSuccess();

  // Hard error (500) — previously swallowed so retries never incremented.
  (AxBIClient.get as jest.Mock).mockRejectedValue({ status: 500 });

  await triggerDownload();

  // Each interval tick should issue another GET because the previous
  // rejection completes and clears isFetching, and increments retries.
  await act(async () => {
    jest.advanceTimersByTime(RETRY_INTERVAL * 3);
    await flushPromises();
  });

  // Immediate attempt + 3 interval ticks.
  expect(AxBIClient.get.mock.calls.length).toBeGreaterThanOrEqual(2);

  jest.clearAllTimers();
  jest.useRealTimers();
});
