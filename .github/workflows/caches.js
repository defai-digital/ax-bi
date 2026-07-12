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

// always use absolute directory
const workspaceDirectory = process.env.GITHUB_WORKSPACE;
const homeDirectory = process.env.HOME;

const assetsConfig = {
  path: [`${workspaceDirectory}/axbi/static/assets`],
  hashFiles: [
    `${workspaceDirectory}/ax-bi-frontend/src/**/*`,
    `${workspaceDirectory}/ax-bi-frontend/packages/**/*`,
    `${workspaceDirectory}/ax-bi-frontend/plugins/**/*`,
    `${workspaceDirectory}/ax-bi-frontend/*.js`,
    `${workspaceDirectory}/ax-bi-frontend/*.json`,
  ],
  // dont use restore keys as it may give an invalid older build
  restoreKeys: '',
};

// Multi-layer cache definition
module.exports = {
  pip: {
    path: [`${homeDirectory}/.cache/pip`],
    hashFiles: [`${workspaceDirectory}/requirements/*.txt`],
  },
  npm: {
    path: [`${homeDirectory}/.npm`],
    hashFiles: [`${workspaceDirectory}/ax-bi-frontend/package-lock.json`],
  },
  assets: assetsConfig,
  // use separate cache for instrumented JS files and regular assets
  // one is built with `npm run build`,
  // another is built with `npm run build-instrumented`
  'instrumented-assets': assetsConfig,
  cypress: {
    path: [`${homeDirectory}/.cache/Cypress`],
    hashFiles: [
      `${workspaceDirectory}/ax-bi-frontend/cypress-base/package-lock.json`,
    ],
  },
};
