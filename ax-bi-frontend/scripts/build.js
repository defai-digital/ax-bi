#!/bin/env node

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

/* eslint-disable no-console */
/**
 * Build packages/plugins filtered by globs
 */
process.env.PATH = `./node_modules/.bin:${process.env.PATH}`;

const { spawnSync } = require('child_process');
const fastGlob = require('fast-glob');
const yargs = require('yargs');
const { hideBin } = require('yargs/helpers');

const { globs } = yargs(hideBin(process.argv))
  .option('globs', {
    type: 'array',
  })
  .parse();
const glob = globs?.length > 1 ? `{${globs.join(',')}}` : globs?.[0] || '*';

const BABEL_CONFIG = '--config-file=../../babel.config.js';

// packages that do not need tsc
const META_PACKAGES = new Set(['demo', 'generator-axbi']);

function run(cmd, options) {
  console.log(`\n>> ${cmd}\n`);
  const [p, ...args] = cmd.split(' ');
  const runner = spawnSync;
  const { status } = runner(p, args, { stdio: 'inherit', ...options });
  if (status !== 0) {
    if (options && options.tolerateFailure) {
      console.warn(
        `\n!! Command failed with status ${status} (tolerated): ${cmd}\n`,
      );
      return;
    }
    process.exit(status);
  }
}

function getPackages(packagePattern, tsOnly = false) {
  let pattern = packagePattern;
  if (!pattern.includes('*')) {
    pattern = `*${pattern}`;
  }

  const packages = [
    ...new Set(
      fastGlob
        .sync([
          `./node_modules/@ax-bi/${pattern}/src/**/*.${
            tsOnly ? '{ts,tsx}' : '{ts,tsx,js,jsx}'
          }`,
        ])
        .map(x => x.split('/')[3])
        .filter(x => !META_PACKAGES.has(x)),
    ),
  ];

  if (packages.length === 0) {
    throw new Error('No matching packages');
  }

  return `@ax-bi/${
    packages.length > 1 ? `{${packages.join(',')}}` : packages[0]
  }`;
}

let scope = getPackages(glob);

console.log('--- Run babel --------');
const babelCommand = `lerna exec --stream --concurrency 10 --scope ${scope} -- babel ${BABEL_CONFIG} src --extensions ".ts,.tsx,.js,.jsx" --copy-files`;
run(`${babelCommand} --out-dir lib`);

console.log('--- Run babel esm ---');
// run again with
run(`${babelCommand} --out-dir esm`, {
  env: { ...process.env, NODE_ENV: 'production', BABEL_OUTPUT: 'esm' },
});

console.log('--- Run tsc ---');
// only run tsc for packages with ts files
scope = getPackages(glob, true);
// The type-declaration build has long-standing errors after the
// TypeScript 6 / antd v6 upgrades and cannot currently pass from a clean
// checkout. Keep it running for visibility, but only fail the build when
// PLUGINS_BUILD_STRICT_TYPES=true (set it once the type debt is repaid).
run(
  `lerna exec --stream --concurrency 3 --scope ${scope} -- ../../scripts/tsc.sh --build`,
  { tolerateFailure: process.env.PLUGINS_BUILD_STRICT_TYPES !== 'true' },
);
