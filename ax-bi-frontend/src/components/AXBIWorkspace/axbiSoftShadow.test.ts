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
import type { AxBITheme } from '@ax-bi/core/theme';
import { axbiSoftShadow } from './index';

const lightTheme = {
  sizeUnit: 4,
  colorBgContainer: '#ffffff',
} as AxBITheme;

const darkTheme = {
  sizeUnit: 4,
  colorBgContainer: '#171d22',
} as AxBITheme;

test('axbiSoftShadow uses cool slate shadow in light mode', () => {
  const shadow = axbiSoftShadow(lightTheme);
  expect(shadow).toContain('rgba(15, 23, 42');
  expect(shadow).not.toContain('rgba(0, 0, 0');
});

test('axbiSoftShadow uses black alpha shadow in dark mode', () => {
  const shadow = axbiSoftShadow(darkTheme);
  expect(shadow).toContain('rgba(0, 0, 0');
  expect(shadow).not.toContain('rgba(15, 23, 42');
});

test('axbiSoftShadow hover is stronger than default', () => {
  const base = axbiSoftShadow(lightTheme, 'default');
  const hover = axbiSoftShadow(lightTheme, 'hover');
  expect(hover).not.toEqual(base);
  expect(hover).toContain('0.1');
});
