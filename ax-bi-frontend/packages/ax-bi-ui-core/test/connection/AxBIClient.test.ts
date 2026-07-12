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
import fetchMock from 'fetch-mock';

import { AxBIClient, AxBIClientClass } from '@ax-bi/ui-core';
import type { AxBIClientInterface } from '@ax-bi/ui-core';
import { LOGIN_GLOB } from './fixtures/constants';

beforeAll(() => fetchMock.mockGlobal());
afterAll(() => fetchMock.hardReset());

describe('AxBIClient', () => {
  beforeAll(() => fetchMock.get(LOGIN_GLOB, { result: '1234' }));

  afterAll(() => fetchMock.removeRoutes().clearHistory());

  afterEach(() => AxBIClient.reset());

  const clientWithGetUrl = AxBIClient as AxBIClientInterface & {
    getUrl: (...args: unknown[]) => string;
  };

  test('exposes configure, init, get, post, postForm, postBlob, delete, put, request, reset, getGuestToken, getCSRFToken, getUrl, isAuthenticated, and reAuthenticate methods', () => {
    expect(typeof AxBIClient.configure).toBe('function');
    expect(typeof AxBIClient.init).toBe('function');
    expect(typeof AxBIClient.get).toBe('function');
    expect(typeof AxBIClient.post).toBe('function');
    expect(typeof AxBIClient.postForm).toBe('function');
    expect(typeof AxBIClient.postBlob).toBe('function');
    expect(typeof AxBIClient.delete).toBe('function');
    expect(typeof AxBIClient.put).toBe('function');
    expect(typeof AxBIClient.request).toBe('function');
    expect(typeof AxBIClient.reset).toBe('function');
    expect(typeof AxBIClient.getGuestToken).toBe('function');
    expect(typeof AxBIClient.getCSRFToken).toBe('function');
    expect(typeof clientWithGetUrl.getUrl).toBe('function');
    expect(typeof AxBIClient.isAuthenticated).toBe('function');
    expect(typeof AxBIClient.reAuthenticate).toBe('function');
  });

  test('throws if you call init, get, post, postForm, postBlob, delete, put, request, getGuestToken, getCSRFToken, getUrl, isAuthenticated, or reAuthenticate before configure', () => {
    expect(AxBIClient.init).toThrow();
    expect(AxBIClient.get).toThrow();
    expect(AxBIClient.post).toThrow();
    expect(AxBIClient.postForm).toThrow();
    expect(AxBIClient.postBlob).toThrow();
    expect(AxBIClient.delete).toThrow();
    expect(AxBIClient.put).toThrow();
    expect(AxBIClient.request).toThrow();
    expect(AxBIClient.getGuestToken).toThrow();
    expect(AxBIClient.getCSRFToken).toThrow();
    expect(clientWithGetUrl.getUrl).toThrow();
    expect(AxBIClient.isAuthenticated).toThrow();
    expect(AxBIClient.reAuthenticate).toThrow();
    expect(AxBIClient.configure).not.toThrow();
  });

  // this also tests that the ^above doesn't throw if configure is called appropriately
  test('calls appropriate AxBIClient methods when configured', async () => {
    expect.assertions(18);
    const mockGetUrl = '/mock/get/url';
    const mockPostUrl = '/mock/post/url';
    const mockRequestUrl = '/mock/request/url';
    const mockPutUrl = '/mock/put/url';
    const mockDeleteUrl = '/mock/delete/url';
    const mockGetPayload = { get: 'payload' };
    const mockPostPayload = { post: 'payload' };
    const mockDeletePayload = { delete: 'ok' };
    const mockPutPayload = { put: 'ok' };
    fetchMock.get(mockGetUrl, mockGetPayload);
    fetchMock.post(mockPostUrl, mockPostPayload);
    fetchMock.delete(mockDeleteUrl, mockDeletePayload);
    fetchMock.put(mockPutUrl, mockPutPayload);
    fetchMock.get(mockRequestUrl, mockGetPayload);

    const initSpy = jest.spyOn(AxBIClientClass.prototype, 'init');
    const getSpy = jest.spyOn(AxBIClientClass.prototype, 'get');
    const postSpy = jest.spyOn(AxBIClientClass.prototype, 'post');
    const putSpy = jest.spyOn(AxBIClientClass.prototype, 'put');
    const deleteSpy = jest.spyOn(AxBIClientClass.prototype, 'delete');
    const authenticatedSpy = jest.spyOn(
      AxBIClientClass.prototype,
      'isAuthenticated',
    );
    const csrfSpy = jest.spyOn(AxBIClientClass.prototype, 'fetchCSRFToken');
    const requestSpy = jest.spyOn(AxBIClientClass.prototype, 'request');
    const getGuestTokenSpy = jest.spyOn(
      AxBIClientClass.prototype,
      'getGuestToken',
    );
    const getUrlSpy = jest.spyOn(AxBIClientClass.prototype, 'getUrl');

    AxBIClient.configure({ appRoot: '/app' });
    expect(clientWithGetUrl.getUrl({ endpoint: '/some/path' })).toContain(
      '/app/some/path',
    );
    expect(getUrlSpy).toHaveBeenCalledTimes(1);

    AxBIClient.configure({});
    await AxBIClient.init();

    expect(initSpy).toHaveBeenCalledTimes(1);
    expect(authenticatedSpy).toHaveBeenCalledTimes(2);
    expect(csrfSpy).toHaveBeenCalledTimes(1);

    await AxBIClient.get({ url: mockGetUrl });
    await AxBIClient.post({ url: mockPostUrl });
    await AxBIClient.delete({ url: mockDeleteUrl });
    await AxBIClient.put({ url: mockPutUrl });
    await AxBIClient.request({ url: mockRequestUrl });

    // Make sure network calls have  Accept: 'application/json' in headers
    const networkCalls = [
      mockGetUrl,
      mockPostUrl,
      mockRequestUrl,
      mockPutUrl,
      mockDeleteUrl,
    ];
    networkCalls.map((url: string) =>
      expect(
        fetchMock.callHistory.calls(url)[0].options?.headers,
      ).toStrictEqual({
        accept: 'application/json',
        'x-csrftoken': '1234',
      }),
    );

    AxBIClient.isAuthenticated();
    await AxBIClient.reAuthenticate();

    AxBIClient.getGuestToken();
    expect(getGuestTokenSpy).toHaveBeenCalledTimes(1);

    expect(initSpy).toHaveBeenCalledTimes(2);
    expect(deleteSpy).toHaveBeenCalledTimes(1);
    expect(putSpy).toHaveBeenCalledTimes(1);
    expect(getSpy).toHaveBeenCalledTimes(1);
    expect(postSpy).toHaveBeenCalledTimes(1);
    expect(requestSpy).toHaveBeenCalledTimes(5); // request rewires to get
    expect(csrfSpy).toHaveBeenCalledTimes(2); // from init() + reAuthenticate()

    initSpy.mockRestore();
    getSpy.mockRestore();
    putSpy.mockRestore();
    deleteSpy.mockRestore();
    requestSpy.mockRestore();
    postSpy.mockRestore();
    authenticatedSpy.mockRestore();
    csrfSpy.mockRestore();
    getUrlSpy.mockRestore();

    fetchMock.clearHistory().removeRoutes();
  });

  test('getCSRFToken() returns existing token when already configured', async () => {
    AxBIClient.configure({ csrfToken: 'my_token' });
    const token = await AxBIClient.getCSRFToken();
    expect(token).toBe('my_token');
  });

  test('guestTokenHeaderName returns the configured header name when instance exists', () => {
    AxBIClient.configure({ guestTokenHeaderName: 'X-Custom-Guest' });
    expect(AxBIClient.guestTokenHeaderName).toBe('X-Custom-Guest');
  });

  test('guestTokenHeaderName returns default X-GuestToken when instance is not configured', () => {
    // Ensure instance is reset (afterEach calls AxBIClient.reset())
    // Access the property without calling configure() first
    expect(AxBIClient.guestTokenHeaderName).toBe('X-GuestToken');
  });
});
