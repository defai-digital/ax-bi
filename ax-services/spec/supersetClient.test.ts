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
import { afterEach, expect, test } from '@jest/globals';

import { buildConfig } from '../src/config';
import { AUTHORIZATION_CONTRACT_VERSION } from '../src/contracts/authorization';
import { SupersetClient } from '../src/supersetClient';

const originalFetch = global.fetch;

afterEach(() => {
  global.fetch = originalFetch;
});

test('checkHealth returns Superset status and forwards request ID', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return new Response('OK', { status: 200 });
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkHealth('request-abc');

  expect(result).toEqual({
    ok: true,
    statusCode: 200,
    url: 'http://127.0.0.1:8088/health',
  });
  expect(seenInput).toBe('http://127.0.0.1:8088/health');
  expect(seenInit?.headers).toEqual({
    'x-request-id': 'request-abc',
  });
});

test('checkPermission posts authorization request to Superset', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json(
      {
        contractVersion: AUTHORIZATION_CONTRACT_VERSION,
        allowed: true,
        reason: 'allowed by Superset',
      },
      { status: 200 },
    );
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
    }),
  );

  const result = await client.checkPermission(
    {
      contractVersion: AUTHORIZATION_CONTRACT_VERSION,
      principal: {
        type: 'user',
        userId: 7,
      },
      resource: {
        type: 'dataset',
        id: 42,
      },
      action: 'read',
    },
    'request-abc',
  );

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: true,
    reason: 'allowed by Superset',
    statusCode: 200,
  });
  expect(seenInput).toBe(
    'http://127.0.0.1:8088/api/v1/security/permissions/check',
  );
  expect(seenInit).toEqual(
    expect.objectContaining({
      method: 'POST',
      headers: {
        authorization: 'Bearer token-123',
        'content-type': 'application/json',
        'x-request-id': 'request-abc',
      },
    }),
  );
  expect(JSON.parse(String(seenInit?.body))).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'user',
      userId: 7,
    },
    resource: {
      type: 'dataset',
      id: 42,
    },
    action: 'read',
  });
});

test('checkPermission fails closed when Superset cannot be reached', async () => {
  global.fetch = async () => {
    throw new Error('connect failed');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkPermission({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    principal: {
      type: 'service',
    },
    resource: {
      type: 'dashboard',
      id: 5,
    },
    action: 'read',
  });

  expect(result).toEqual({
    contractVersion: AUTHORIZATION_CONTRACT_VERSION,
    allowed: false,
    error: 'connect failed',
  });
});

test('probeMetadata returns sanitized Superset metadata summary', async () => {
  let seenInput: RequestInfo | URL | undefined;
  let seenInit: RequestInit | undefined;
  global.fetch = async (input, init) => {
    seenInput = input;
    seenInit = init;
    return Response.json(
      {
        permissions: ['can_read'],
        result: {
          add_columns: ['dashboard_title'],
        },
        edit_columns: ['slug'],
      },
      { status: 200 },
    );
  };
  const client = new SupersetClient(
    buildConfig({
      AX_SUPERSET_INTERNAL_TOKEN: 'token-123',
      AX_SUPERSET_METADATA_PATH: '/api/v1/dashboard/_info',
    }),
  );

  const result = await client.probeMetadata('request-abc');

  expect(result).toEqual({
    ok: true,
    statusCode: 200,
    url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
    keyCount: 3,
    keys: ['edit_columns', 'permissions', 'result'],
  });
  expect(seenInput).toBe('http://127.0.0.1:8088/api/v1/dashboard/_info');
  expect(seenInit?.headers).toEqual({
    authorization: 'Bearer token-123',
    'x-request-id': 'request-abc',
  });
});

test('probeMetadata returns an error result when fetch fails', async () => {
  global.fetch = async () => {
    throw new Error('metadata failed');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.probeMetadata();

  expect(result).toEqual({
    ok: false,
    error: 'metadata failed',
    url: 'http://127.0.0.1:8088/api/v1/dashboard/_info',
  });
});

test('checkHealth returns an error result when fetch fails', async () => {
  global.fetch = async () => {
    throw new Error('connect failed');
  };
  const client = new SupersetClient(buildConfig({}));

  const result = await client.checkHealth();

  expect(result).toEqual({
    ok: false,
    error: 'connect failed',
    url: 'http://127.0.0.1:8088/health',
  });
});
