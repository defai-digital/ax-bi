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
import type { ValidationIssue } from './themeStructureValidation';

/** WCAG 2.2 minimum contrast ratio for normal text (SC 1.4.3). */
const TEXT_CONTRAST_MIN = 4.5;
/** WCAG 2.2 minimum contrast ratio for UI components and graphical objects (SC 1.4.11). */
const UI_CONTRAST_MIN = 3;

/** Token pairs worth checking, each with the WCAG threshold that applies to it. */
const TEXT_TOKENS = ['colorText', 'colorTextSecondary', 'colorLink'];
const UI_TOKENS = [
  'colorPrimary',
  'colorInfo',
  'colorSuccess',
  'colorWarning',
  'colorError',
];
const BACKGROUND_TOKENS = [
  'colorBgBase',
  'colorBgLayout',
  'colorBgContainer',
  'colorBgElevated',
];

function parseHexColor(value: unknown): [number, number, number] | null {
  if (typeof value !== 'string') return null;
  let hex = value.trim();
  if (!hex.startsWith('#')) return null;
  hex = hex.slice(1);
  if (hex.length === 3) {
    hex = hex
      .split('')
      .map(ch => ch + ch)
      .join('');
  }
  if (hex.length !== 6 && hex.length !== 8) return null;
  const r = parseInt(hex.slice(0, 2), 16);
  const g = parseInt(hex.slice(2, 4), 16);
  const b = parseInt(hex.slice(4, 6), 16);
  if ([r, g, b].some(Number.isNaN)) return null;
  return [r, g, b];
}

/** WCAG relative luminance, https://www.w3.org/TR/WCAG22/#dfn-relative-luminance */
function relativeLuminance([r, g, b]: [number, number, number]): number {
  const channel = (c: number) => {
    const s = c / 255;
    return s <= 0.03928 ? s / 12.92 : ((s + 0.055) / 1.055) ** 2.4;
  };
  return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b);
}

/**
 * WCAG contrast ratio between two colors, https://www.w3.org/TR/WCAG22/#dfn-contrast-ratio
 * Returns null if either color cannot be parsed (e.g. not a hex string --
 * this is a best-effort check, not a full CSS color parser).
 */
export function contrastRatio(colorA: string, colorB: string): number | null {
  const rgbA = parseHexColor(colorA);
  const rgbB = parseHexColor(colorB);
  if (!rgbA || !rgbB) return null;
  const lA = relativeLuminance(rgbA);
  const lB = relativeLuminance(rgbB);
  const lighter = Math.max(lA, lB);
  const darker = Math.min(lA, lB);
  return (lighter + 0.05) / (darker + 0.05);
}

/**
 * Checks contrast between token pairs that are BOTH present in the theme
 * being edited (e.g. an admin overriding colorText alongside colorBgContainer).
 * This intentionally does not merge in the base/default theme's colors --
 * a partial override (the common case) can't know what the effective
 * background will be without simulating the full merge, so we only flag
 * pairs the admin has explicitly set together, to avoid false positives.
 *
 * Only produces warnings (SC 1.4.3 / 1.4.11 are AA-level, non-blocking here
 * to match the rest of theme validation's "warn, don't block" approach) --
 * an admin may have a deliberate reason for lower contrast.
 */
export function validateThemeContrast(
  tokens: Record<string, unknown>,
): ValidationIssue[] {
  const issues: ValidationIssue[] = [];

  const checkPairs = (foregroundTokens: string[], threshold: number) => {
    foregroundTokens.forEach(fgName => {
      const fgValue = tokens[fgName];
      if (fgValue === undefined) return;

      BACKGROUND_TOKENS.forEach(bgName => {
        const bgValue = tokens[bgName];
        if (bgValue === undefined) return;

        const ratio = contrastRatio(fgValue as string, bgValue as string);
        if (ratio === null || ratio >= threshold) return;

        issues.push({
          tokenName: fgName,
          severity: 'warning',
          message:
            `${fgName} (${fgValue}) on ${bgName} (${bgValue}) has a contrast ` +
            `ratio of ${ratio.toFixed(2)}:1, below the WCAG AA minimum of ` +
            `${threshold}:1 for ${threshold === TEXT_CONTRAST_MIN ? 'text' : 'UI components and chart marks'}.`,
        });
      });
    });
  };

  checkPairs(TEXT_TOKENS, TEXT_CONTRAST_MIN);
  checkPairs(UI_TOKENS, UI_CONTRAST_MIN);

  return issues;
}
