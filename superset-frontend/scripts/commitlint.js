#!/usr/bin/env node

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

/**
 * Check commit messages only for the first commit in branch.
 */
const { execSync, spawnSync } = require('child_process');

if (process.argv.includes('--help') || process.argv.includes('-h')) {
  process.stdout.write(`Usage: node scripts/commitlint.js [env-var-name]

Check commit messages using commitlint.

Arguments:
  env-var-name  Environment variable containing the commit message
                (default: GIT_PARAMS)

Options:
  --help, -h    Show this help message
`);
  process.exit(0);
}

const envVariable = process.argv[2] || 'GIT_PARAMS';

if (!envVariable || !process.env[envVariable]) {
  process.stderr.write(
    `Please provide a commit message via \`${envVariable}={Your Message}\`.\n`,
  );
  process.exit(1);
}
if (
  execSync('git rev-list --count HEAD ^master', {
    encoding: 'utf-8',
  }).trim() === '0'
) {
  const { error, status } = spawnSync(`commitlint`, ['-E', envVariable], {
    stdio: 'inherit',
  });
  if (error) {
    process.stderr.write(`Unable to run commitlint: ${error.message}\n`);
    process.exit(1);
  }
  process.exit(status);
}
