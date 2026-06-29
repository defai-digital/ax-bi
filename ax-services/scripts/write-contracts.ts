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

import { annotationLayerListContractSchemas } from '../src/contracts/annotationLayerList';
import { assetSearchContractSchemas } from '../src/contracts/assetSearch';
import { authorizationContractSchemas } from '../src/contracts/authorization';
import { chartListContractSchemas } from '../src/contracts/chartList';
import { dashboardListContractSchemas } from '../src/contracts/dashboardList';
import { databaseListContractSchemas } from '../src/contracts/databaseList';
import { datasetListContractSchemas } from '../src/contracts/datasetList';
import { reportListContractSchemas } from '../src/contracts/reportList';
import { runtimeContractSchemas } from '../src/contracts/runtime';
import { savedQueryListContractSchemas } from '../src/contracts/savedQueryList';
import { tagListContractSchemas } from '../src/contracts/tagList';
import { taskListContractSchemas } from '../src/contracts/taskList';

const outputDir = join(__dirname, '..', 'contracts');

const contractFiles = {
  'annotation-layer-list.v1.schema.json': annotationLayerListContractSchemas,
  'asset-search.v1.schema.json': assetSearchContractSchemas,
  'authorization.v1.schema.json': authorizationContractSchemas,
  'chart-list.v1.schema.json': chartListContractSchemas,
  'dashboard-list.v1.schema.json': dashboardListContractSchemas,
  'database-list.v1.schema.json': databaseListContractSchemas,
  'dataset-list.v1.schema.json': datasetListContractSchemas,
  'report-list.v1.schema.json': reportListContractSchemas,
  'runtime.v1.schema.json': runtimeContractSchemas,
  'saved-query-list.v1.schema.json': savedQueryListContractSchemas,
  'tag-list.v1.schema.json': tagListContractSchemas,
  'task-list.v1.schema.json': taskListContractSchemas,
};

mkdirSync(outputDir, { recursive: true });

for (const [filename, schemas] of Object.entries(contractFiles)) {
  writeFileSync(
    join(outputDir, filename),
    `${JSON.stringify(schemas, null, 2)}\n`,
    'utf8',
  );
}
