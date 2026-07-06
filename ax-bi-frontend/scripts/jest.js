#!/usr/bin/env node

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

const { spawnSync } = require('node:child_process');

const DEFAULT_ARGS = ['--max-workers=80%', '--workerIdleMemoryLimit=1536MB'];
const args = process.argv.slice(2);

const hasWorkerControlArg = args.some(
  arg =>
    arg === '--runInBand' ||
    arg === '-i' ||
    arg === '--maxWorkers' ||
    arg === '--max-workers' ||
    arg.startsWith('--maxWorkers=') ||
    arg.startsWith('--max-workers='),
);

const hasWorkerMemoryLimitArg = args.some(
  arg =>
    arg === '--workerIdleMemoryLimit' ||
    arg.startsWith('--workerIdleMemoryLimit='),
);

const jestArgs = [
  ...(hasWorkerControlArg ? [] : [DEFAULT_ARGS[0]]),
  ...(hasWorkerMemoryLimitArg ? [] : [DEFAULT_ARGS[1]]),
  ...args,
];
const result = spawnSync(
  process.execPath,
  [require.resolve('jest/bin/jest'), ...jestArgs],
  { stdio: 'inherit' },
);

if (result.error) {
  console.error(result.error);
  process.exit(1);
}

process.exit(result.status ?? 1);
