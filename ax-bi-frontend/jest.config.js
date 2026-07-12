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
// timezone for unit tests
process.env.TZ = 'America/New_York';
module.exports = {
  testRegex:
    '\\/ax-bi-frontend\\/(spec|src|plugins|packages|tools)\\/.*(_spec|\\.test)\\.[jt]sx?$',
  moduleNameMapper: {
    '\\.(css|less|geojson)$': '<rootDir>/spec/__mocks__/mockExportObject.js',
    '\\.(gif|ttf|eot|png|jpg)$': '<rootDir>/spec/__mocks__/mockExportString.js',
    '\\.svg$': '<rootDir>/spec/__mocks__/svgrMock.tsx',
    '^src/(.*)$': '<rootDir>/src/$1',
    '^spec/(.*)$': '<rootDir>/spec/$1',
    // Map AX BI workspaces directly to source so tests do not depend on
    // package-manager symlinks left over from a previous checkout layout.
    '^@ax-bi/(core|ui-core|chart-controls|switchboard)/(.*)$':
      '<rootDir>/packages/ax-bi-$1/src/$2',
    '^@ax-bi/(core|ui-core|chart-controls|switchboard)$':
      '<rootDir>/packages/ax-bi-$1/src',
    '^@ax-bi/([^/]+)/(.*)$': '<rootDir>/plugins/$1/src/$2',
    '^@ax-bi/([^/]+)$': '<rootDir>/plugins/$1/src',
  },
  testEnvironment: '<rootDir>/spec/helpers/jsDomWithFetchAPI.ts',
  modulePathIgnorePatterns: [
    '<rootDir>/packages/generator-axbi',
    '<rootDir>/packages/.*/esm',
    '<rootDir>/packages/.*/lib',
    '<rootDir>/plugins/.*/esm',
    '<rootDir>/plugins/.*/lib',
    // Ignore build artifacts that contain duplicate package.json or mock files
    '<rootDir>/storybook-static',
    // Ignore duplicate __mocks__ at package root level (e.g., packages/ax-bi-ui-core/__mocks__)
    // but not test __mocks__ directories (e.g., packages/ax-bi-ui-core/test/__mocks/)
    '<rootDir>/packages/[^/]+/__mocks__',
  ],
  setupFilesAfterEnv: ['<rootDir>/spec/helpers/setup.ts'],
  snapshotSerializers: ['@emotion/jest/serializer'],
  testEnvironmentOptions: {
    globalsCleanup: true,
    url: 'http://localhost',
  },
  collectCoverageFrom: [
    'src/**/*.{js,jsx,ts,tsx}',
    '{packages,plugins}/**/src/**/*.{js,jsx,ts,tsx}',
    '!**/*.stories.*',
  ],
  coverageDirectory: '<rootDir>/coverage/',
  coveragePathIgnorePatterns: [
    'coverage/',
    'node_modules/',
    'public/',
    'tmp/',
    'dist/',
  ],
  coverageReporters: ['lcov', 'json-summary', 'html', 'text'],
  transformIgnorePatterns: [
    'node_modules/(?!@formatjs/.*|d3-.*|delaunator|robust-predicates|internmap|@mapbox/tiny-sdf|remark-gfm|(?!@ngrx|(?!deck.gl)|d3-scale)|markdown-table|micromark-*.|decode-named-character-reference|character-entities|mdast-util-*.|unist-util-*.|ccount|escape-string-regexp|nanoid|uuid|@rjsf/*.|antd|@ant-design/.*|echarts|zrender|fetch-mock|pretty-ms|parse-ms|ol|@babel/runtime|@emotion|cheerio|cheerio/lib|parse5|dom-serializer|entities|htmlparser2|rehype-sanitize|hast-util-sanitize|unified|unist-.*|hast-.*|rehype-.*|remark-.*|mdast-.*|micromark-.*|parse-entities|property-information|space-separated-tokens|comma-separated-tokens|bail|devlop|zwitch|longest-streak|geostyler|geostyler-.*|(?!geostyler)lodash|react-error-boundary|react-json-tree|react-base16-styling|lodash-es|rbush|quickselect|react-diff-viewer-continued|react-resize-detector|storybook/*.|@storybook/.*|json-stringify-pretty-compact)',
  ],
  preset: 'ts-jest',
  transform: {
    '^.+\\.(js|jsx|ts|tsx)$': 'babel-jest',
  },
  moduleFileExtensions: ['ts', 'tsx', 'js', 'jsx', 'json', 'node'],
  globals: {
    __DEV__: true,
    caches: true,
  },
  reporters: [
    'default',
    [
      './node_modules/jest-html-reporter',
      {
        pageTitle: 'Test Report',
      },
    ],
  ],
  testTimeout: 20000,
};
