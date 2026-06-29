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
import { mkdirSync, writeFileSync } from 'fs';
import { join } from 'path';

import { assetSearchContractSchemas } from '../src/contracts/assetSearch';
import { authorizationContractSchemas } from '../src/contracts/authorization';
import { chartListContractSchemas } from '../src/contracts/chartList';
import { dashboardListContractSchemas } from '../src/contracts/dashboardList';
import { datasetListContractSchemas } from '../src/contracts/datasetList';
import { runtimeContractSchemas } from '../src/contracts/runtime';

const outputDir = join(__dirname, '..', 'contracts');

const contractFiles = {
  'asset-search.v1.schema.json': assetSearchContractSchemas,
  'authorization.v1.schema.json': authorizationContractSchemas,
  'chart-list.v1.schema.json': chartListContractSchemas,
  'dashboard-list.v1.schema.json': dashboardListContractSchemas,
  'dataset-list.v1.schema.json': datasetListContractSchemas,
  'runtime.v1.schema.json': runtimeContractSchemas,
};

mkdirSync(outputDir, { recursive: true });

for (const [filename, schemas] of Object.entries(contractFiles)) {
  writeFileSync(
    join(outputDir, filename),
    `${JSON.stringify(schemas, null, 2)}\n`,
    'utf8',
  );
}
