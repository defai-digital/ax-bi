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
import { readFileSync } from 'fs';
import { join } from 'path';

import { expect, test } from '@jest/globals';

import { assetSearchContractSchemas } from '../src/contracts/assetSearch';
import { authorizationContractSchemas } from '../src/contracts/authorization';
import { chartListContractSchemas } from '../src/contracts/chartList';
import { dashboardListContractSchemas } from '../src/contracts/dashboardList';
import { runtimeContractSchemas } from '../src/contracts/runtime';

function readContractArtifact(filename: string): unknown {
  return JSON.parse(
    readFileSync(join(__dirname, '..', 'contracts', filename), 'utf8'),
  );
}

test('runtime contract artifact matches TypeScript source', () => {
  expect(readContractArtifact('runtime.v1.schema.json')).toEqual(
    runtimeContractSchemas,
  );
});

test('authorization contract artifact matches TypeScript source', () => {
  expect(readContractArtifact('authorization.v1.schema.json')).toEqual(
    authorizationContractSchemas,
  );
});

test('asset search contract artifact matches TypeScript source', () => {
  expect(readContractArtifact('asset-search.v1.schema.json')).toEqual(
    assetSearchContractSchemas,
  );
});

test('dashboard list contract artifact matches TypeScript source', () => {
  expect(readContractArtifact('dashboard-list.v1.schema.json')).toEqual(
    dashboardListContractSchemas,
  );
});

test('chart list contract artifact matches TypeScript source', () => {
  expect(readContractArtifact('chart-list.v1.schema.json')).toEqual(
    chartListContractSchemas,
  );
});
