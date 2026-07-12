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
/* eslint-disable theme-colors/no-literal-colors */
import { type SerializableThemeConfig, ThemeAlgorithm } from './types';

const exampleThemes: Record<string, SerializableThemeConfig> = {
  axbi: {
    token: {
      colorBgElevated: '#fafafa',
    },
  },
  axbiDark: {
    token: {},
    algorithm: ThemeAlgorithm.DARK,
  },
  axbiCompact: {
    token: {},
    algorithm: ThemeAlgorithm.COMPACT,
  },
  /**
   * Japandi calm — paper + ink + stone (aligned with AX Office library).
   * Harmony, Ma, soft teal brand; not a cool SaaS gray shell.
   */
  japandi: {
    token: {
      colorPrimary: '#0f766e',
      colorLink: '#0f766e',
      colorError: '#b54a38',
      colorWarning: '#9a6a1c',
      colorSuccess: '#2f7a5c',
      colorInfo: '#6d5a9a',
      borderRadius: 8,
      colorBgBase: '#fffcf8',
      colorBgLayout: '#f4f1ec',
      colorBgContainer: '#fffcf8',
      colorBgElevated: '#fffcf8',
      colorBgSpotlight: '#efeae3',
      colorBorder: '#e2ddd4',
      colorBorderSecondary: '#ebe6df',
      colorText: '#2c2a26',
      colorTextSecondary: '#6b6560',
      colorTextTertiary: '#9a948c',
      colorTextPlaceholder: '#9a948c',
    },
    algorithm: ThemeAlgorithm.DEFAULT,
  },
  japandiDark: {
    token: {
      colorPrimary: '#2dd4bf',
      colorLink: '#2dd4bf',
      colorError: '#f0a090',
      colorWarning: '#e0b35a',
      colorSuccess: '#7dcfb0',
      colorInfo: '#a78bfa',
      borderRadius: 8,
      colorBgBase: '#161412',
      colorBgLayout: '#100f0d',
      colorBgContainer: '#1f1d1a',
      colorBgElevated: '#2a2723',
      colorBgSpotlight: '#35312c',
      colorBorder: '#35312c',
      colorBorderSecondary: '#2a2723',
      colorText: '#f3efe8',
      colorTextSecondary: '#a39e96',
      colorTextTertiary: '#6f6a63',
      colorTextPlaceholder: '#6f6a63',
    },
    algorithm: ThemeAlgorithm.DARK,
  },
  funky: {
    token: {
      colorPrimary: '#f759ab', // hot pink
      colorSuccess: '#52c41a',
      colorWarning: '#faad14',
      colorError: '#ff4d4f',
      colorInfo: '#40a9ff',
      borderRadius: 12,
      fontFamily: 'Comic Sans MS, cursive',
    },
    algorithm: ThemeAlgorithm.DEFAULT,
  },
  funkyDark: {
    token: {
      colorPrimary: '#f759ab', // hot pink
      colorSuccess: '#52c41a',
      colorWarning: '#faad14',
      colorError: '#ff4d4f',
      colorInfo: '#40a9ff',
      borderRadius: 12,
      fontFamily: 'Comic Sans MS, cursive',
    },
    algorithm: ThemeAlgorithm.DARK,
  },
};
export default exampleThemes;
