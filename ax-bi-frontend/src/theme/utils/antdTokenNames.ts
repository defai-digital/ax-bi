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
import { theme } from 'antd';

/**
 * AxBI-specific custom tokens that extend Ant Design's token system.
 * These keys are derived from the AxBISpecificTokens interface to ensure consistency.
 */
const AXBI_CUSTOM_TOKENS: Set<string> = new Set([
  // Font extensions (fontWeightStrong is an Ant Design token, not AxBI-specific)
  'fontSizeXS',
  'fontSizeXXL',
  'fontWeightNormal',
  'fontWeightLight',

  // Brand tokens
  'brandIconMaxWidth',
  'brandLogoAlt',
  'brandLogoUrl',
  'brandLogoMargin',
  'brandLogoHref',
  'brandLogoHeight',

  // Spinner tokens
  'brandSpinnerUrl',
  'brandSpinnerSvg',

  // ECharts tokens
  'echartsOptionsOverrides',
  'echartsOptionsOverridesByChartType',

  // Font loading
  'fontUrls',

  // Label variant tokens — Published/Draft (dashboard status)
  'labelPublishedColor',
  'labelPublishedBg',
  'labelPublishedBorderColor',
  'labelPublishedIconColor',
  'labelDraftColor',
  'labelDraftBg',
  'labelDraftBorderColor',
  'labelDraftIconColor',

  // Label variant tokens — Dataset type (Physical/Virtual)
  'labelDatasetPhysicalColor',
  'labelDatasetPhysicalBg',
  'labelDatasetPhysicalBorderColor',
  'labelDatasetPhysicalIconColor',
  'labelDatasetVirtualColor',
  'labelDatasetVirtualBg',
  'labelDatasetVirtualBorderColor',
  'labelDatasetVirtualIconColor',

  // Editor tokens
  'colorEditorSelection',

  // Secondary button tokens
  'buttonSecondaryColor',
  'buttonSecondaryBg',
  'buttonSecondaryBorderColor',
  'buttonSecondaryHoverColor',
  'buttonSecondaryHoverBg',
  'buttonSecondaryHoverBorderColor',
  'buttonSecondaryActiveColor',
  'buttonSecondaryActiveBg',
  'buttonSecondaryActiveBorderColor',
]);

/**
 * Lazy-loaded cache of valid token names.
 * Combines Ant Design tokens (extracted at runtime) + AxBI custom tokens.
 */
let validTokenNamesCache: Set<string> | undefined;

/**
 * Get all valid token names (Ant Design + AxBI custom).
 * Uses lazy loading and caching for performance.
 */
function getValidTokenNames(): Set<string> {
  if (validTokenNamesCache === undefined) {
    // Extract all token names from Ant Design's default theme
    const antdTokens = theme.getDesignToken();
    const antdTokenNames = Object.keys(antdTokens);

    // Combine with AxBI custom tokens
    validTokenNamesCache = new Set([...antdTokenNames, ...AXBI_CUSTOM_TOKENS]);
  }
  return validTokenNamesCache;
}

/**
 * Check if a token name is valid (recognized by Ant Design OR AxBI).
 * @param tokenName - The token name to validate
 * @returns true if the token is recognized, false otherwise
 */
export function isValidTokenName(tokenName: string): boolean {
  return getValidTokenNames().has(tokenName);
}

/**
 * Check if a token is a AxBI custom token (not from Ant Design).
 * @param tokenName - The token name to check
 * @returns true if it's a AxBI-specific token
 */
export function isAxBICustomToken(tokenName: string): boolean {
  return AXBI_CUSTOM_TOKENS.has(tokenName);
}

/**
 * Get all valid token names, categorized by source.
 * Useful for debugging and testing.
 */
export function getAllValidTokenNames(): {
  antdTokens: string[];
  axbiTokens: string[];
  total: number;
} {
  const allTokens = getValidTokenNames();
  const antdTokens = Array.from(allTokens).filter(t => !isAxBICustomToken(t));
  const axbiTokens: string[] = Array.from(AXBI_CUSTOM_TOKENS);

  return {
    antdTokens,
    axbiTokens,
    total: allTokens.size,
  };
}
