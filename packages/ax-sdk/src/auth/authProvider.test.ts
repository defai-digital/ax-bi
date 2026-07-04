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

import { AuthProvider } from './authProvider.js';

describe('AuthProvider', () => {
  describe('token auth', () => {
    test('seeds accessToken from config', () => {
      const auth = new AuthProvider(
        { type: 'token', accessToken: 'my-jwt' },
        'http://localhost:8088',
      );
      expect(auth.isAuthenticated).toBe(true);
      expect(auth.getAccessToken()).toBe('my-jwt');
      expect(auth.getAuthHeaders()).toEqual({
        Authorization: 'Bearer my-jwt',
      });
    });

    test('login is a no-op for token auth', async () => {
      const auth = new AuthProvider(
        { type: 'token', accessToken: 'tok' },
        'http://localhost:8088',
      );
      await expect(auth.login()).resolves.toBeUndefined();
    });
  });

  describe('guest token auth', () => {
    test('uses guestToken as bearer token', () => {
      const auth = new AuthProvider(
        { type: 'guestToken', guestToken: 'guest-abc' },
        'http://localhost:8088',
      );
      expect(auth.isAuthenticated).toBe(true);
      expect(auth.getAuthHeaders()).toEqual({
        Authorization: 'Bearer guest-abc',
      });
    });
  });

  describe('API key auth', () => {
    test('uses default Authorization header', () => {
      const auth = new AuthProvider(
        { type: 'apiKey', apiKey: 'key-123' },
        'http://localhost:8088',
      );
      expect(auth.isAuthenticated).toBe(true);
      expect(auth.getAuthHeaders()).toEqual({
        Authorization: 'Bearer key-123',
      });
    });

    test('uses custom header name and prefix', () => {
      const auth = new AuthProvider(
        { type: 'apiKey', apiKey: 'key-123', headerName: 'X-API-Key', headerPrefix: '' },
        'http://localhost:8088',
      );
      expect(auth.getAuthHeaders()).toEqual({
        'X-API-Key': 'key-123',
      });
    });
  });

  describe('credentials auth', () => {
    test('is not authenticated until login is called', () => {
      const auth = new AuthProvider(
        { type: 'credentials', username: 'admin', password: 'admin' },
        'http://localhost:8088',
      );
      expect(auth.isAuthenticated).toBe(false);
      expect(auth.getAccessToken()).toBeNull();
    });

    test('setAccessToken updates the token', () => {
      const auth = new AuthProvider(
        { type: 'credentials', username: 'admin', password: 'admin' },
        'http://localhost:8088',
      );
      auth.setAccessToken('new-token');
      expect(auth.isAuthenticated).toBe(true);
      expect(auth.getAccessToken()).toBe('new-token');
      expect(auth.getAuthHeaders()).toEqual({
        Authorization: 'Bearer new-token',
      });
    });
  });
});
