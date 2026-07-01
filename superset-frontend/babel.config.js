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
const packageConfig = require('./package');
const coreJsVersion = require('core-js/package.json').version;
const isTest =
  process.env.NODE_ENV === 'test' || process.env.BABEL_ENV === 'test';

module.exports = {
  sourceMaps: true,
  sourceType: 'module',
  retainLines: true,
  assumptions: {
    noDocumentAll: true,
    privateFieldsAsProperties: true,
    setPublicClassFields: true,
  },
  presets: [
    [
      '@babel/preset-env',
      {
        modules: false,
        shippedProposals: true,
        targets: packageConfig.browserslist,
      },
    ],
    [
      '@babel/preset-react',
      {
        development: process.env.BABEL_ENV === 'development',
        runtime: 'automatic',
      },
    ],
    '@babel/preset-typescript',
  ],
  plugins: [
    [
      'polyfill-corejs3',
      {
        method: 'usage-global',
        proposals: true,
        version: coreJsVersion,
      },
    ],
    '@babel/plugin-transform-export-namespace-from',
    ['@babel/plugin-transform-runtime', { corejs: 3 }],
    ...(!isTest
      ? [
          [
            '@emotion/babel-plugin',
            {
              autoLabel: 'dev-only',
              labelFormat: '[local]',
            },
          ],
        ]
      : []),
  ],
  env: {
    // Setup a different config for tests as they run in node instead of a browser
    test: {
      presets: [
        [
          '@babel/preset-env',
          {
            shippedProposals: true,
            modules: 'commonjs',
            targets: { node: 'current' },
          },
        ],
        [
          '@babel/preset-react',
          {
            development: process.env.BABEL_ENV === 'development',
            runtime: 'automatic',
          },
        ],
        '@babel/preset-typescript',
      ],
      plugins: [
        [
          'polyfill-corejs3',
          {
            method: 'usage-global',
            proposals: true,
            version: coreJsVersion,
          },
        ],
        'babel-plugin-dynamic-import-node',
        '@babel/plugin-transform-export-namespace-from',
      ],
    },
    // build instrumented code for testing code coverage with Cypress
    instrumented: {
      plugins: [
        [
          'istanbul',
          {
            exclude: ['plugins/**/*', 'packages/**/*'],
          },
        ],
      ],
    },
    production: {
      plugins: [
        [
          'babel-plugin-jsx-remove-data-test-id',
          {
            // The plugin matches attribute names exactly (no prefix match),
            // so each data-test* attribute must be listed explicitly.
            attributes: [
              'data-test',
              'data-test-drag-source-id',
              'data-test-drop-target-id',
            ],
          },
        ],
      ],
    },
    testableProduction: {
      plugins: [],
    },
  },
  overrides: [
    {
      test: './plugins/plugin-chart-handlebars/node_modules/just-handlebars-helpers/*',
      sourceType: 'unambiguous',
    },
  ],
};
