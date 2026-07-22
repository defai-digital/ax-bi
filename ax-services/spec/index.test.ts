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
import { expect, jest, test } from '@jest/globals';

import { start } from '../src/index';

test('start handles invalid configuration without rejecting', async () => {
  const previousPort = process.env['AX_SERVICES_PORT'];
  const error = jest.spyOn(console, 'error').mockImplementation(() => {});
  const exit = jest
    .spyOn(process, 'exit')
    .mockImplementation((() => undefined) as never);

  try {
    process.env['AX_SERVICES_PORT'] = 'not-a-port';

    await expect(start()).resolves.toBeUndefined();

    expect(exit).toHaveBeenCalledWith(1);
    expect(error).toHaveBeenCalledTimes(1);
    const logged = JSON.parse(String(error.mock.calls[0]?.[0])) as Record<
      string,
      unknown
    >;
    expect(logged['level']).toBe('error');
    expect(logged['message']).toBe('ax-services failed to start');
    expect(logged['error']).toMatchObject({
      message: 'AX_SERVICES_PORT must be a positive integer',
      name: 'Error',
    });
  } finally {
    if (previousPort === undefined) {
      delete process.env['AX_SERVICES_PORT'];
    } else {
      process.env['AX_SERVICES_PORT'] = previousPort;
    }
    error.mockRestore();
    exit.mockRestore();
  }
});
