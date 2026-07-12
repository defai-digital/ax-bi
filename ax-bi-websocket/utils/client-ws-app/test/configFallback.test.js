/*
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
const assert = require('node:assert');
const http = require('node:http');
const test = require('node:test');

test('client app renders with the example config when local config is missing', async () => {
  const app = require('../app');
  const server = app.listen(0);
  await new Promise(resolve => {
    server.once('listening', resolve);
  });

  try {
    const { port } = server.address();
    const response = await new Promise((resolve, reject) => {
      http
        .get(`http://127.0.0.1:${port}/?sockets=1`, resolve)
        .on('error', reject);
    });
    const body = await new Promise((resolve, reject) => {
      let data = '';
      response.setEncoding('utf8');
      response.on('data', chunk => {
        data += chunk;
      });
      response.on('end', () => resolve(data));
      response.on('error', reject);
    });

    assert.equal(response.statusCode, 200);
    assert.match(body, /async-token/);
  } finally {
    await new Promise(resolve => {
      server.close(resolve);
    });
  }
});
