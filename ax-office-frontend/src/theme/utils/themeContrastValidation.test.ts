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
import { contrastRatio, validateThemeContrast } from './themeContrastValidation';

test('contrastRatio computes the WCAG ratio between black and white as 21:1', () => {
  expect(contrastRatio('#000000', '#ffffff')).toBeCloseTo(21, 0);
});

test('contrastRatio computes 1:1 for identical colors', () => {
  expect(contrastRatio('#336699', '#336699')).toBeCloseTo(1, 5);
});

test('contrastRatio is order-independent', () => {
  const a = contrastRatio('#111111', '#eeeeee');
  const b = contrastRatio('#eeeeee', '#111111');
  expect(a).toBeCloseTo(b as number, 5);
});

test('contrastRatio expands 3-digit hex shorthand', () => {
  expect(contrastRatio('#000', '#fff')).toBeCloseTo(21, 0);
});

test('contrastRatio returns null for unparseable colors', () => {
  expect(contrastRatio('not-a-color', '#ffffff')).toBeNull();
  expect(contrastRatio('rgb(0,0,0)', '#ffffff')).toBeNull();
});

test('validateThemeContrast is silent when no background token is set alongside a foreground token', () => {
  const issues = validateThemeContrast({ colorText: '#ffffff' });
  expect(issues).toHaveLength(0);
});

test('validateThemeContrast warns when text contrast is below the 4.5:1 AA minimum', () => {
  const issues = validateThemeContrast({
    colorText: '#777777',
    colorBgContainer: '#666666',
  });

  expect(issues).toHaveLength(1);
  expect(issues[0]).toMatchObject({
    tokenName: 'colorText',
    severity: 'warning',
  });
  expect(issues[0].message).toMatch(/4\.5:1/);
  expect(issues[0].message).toMatch(/text/);
});

test('validateThemeContrast does not warn when text contrast clears the 4.5:1 AA minimum', () => {
  const issues = validateThemeContrast({
    colorText: '#ffffff',
    colorBgContainer: '#000000',
  });

  expect(issues).toHaveLength(0);
});

test('validateThemeContrast uses the looser 3:1 minimum for UI/semantic tokens like colorPrimary', () => {
  // ~3.95:1 -- fails the 4.5:1 text minimum but clears the 3:1 UI minimum
  const passingUiPair = validateThemeContrast({
    colorPrimary: '#808080',
    colorBgContainer: '#ffffff',
  });
  expect(passingUiPair).toHaveLength(0);

  const failingTextPair = validateThemeContrast({
    colorText: '#808080',
    colorBgContainer: '#ffffff',
  });
  expect(failingTextPair).toHaveLength(1);
  expect(failingTextPair[0].message).toMatch(/text/);
});

test('validateThemeContrast checks a foreground token against every background token present', () => {
  const issues = validateThemeContrast({
    colorText: '#333333',
    colorBgContainer: '#3a3a3a',
    colorBgLayout: '#2f2f2f',
  });

  expect(issues).toHaveLength(2);
  expect(issues.map(i => i.tokenName)).toEqual(['colorText', 'colorText']);
});

test('validateThemeContrast ignores non-hex color values without throwing', () => {
  expect(() =>
    validateThemeContrast({
      colorText: 'rgb(255, 255, 255)',
      colorBgContainer: '#000000',
    }),
  ).not.toThrow();
});
