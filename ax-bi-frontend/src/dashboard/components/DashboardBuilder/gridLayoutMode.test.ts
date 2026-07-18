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
import {
  DASHBOARD_GRID_COMPACT_BREAKPOINT,
  DASHBOARD_GRID_STACK_BREAKPOINT,
  getGridLayoutMode,
} from './gridLayoutMode';

test('returns standard at every width when DASHBOARD_RESPONSIVE is off', () => {
  expect(
    getGridLayoutMode(400, { responsiveEnabled: false, editMode: false }),
  ).toBe('standard');
  expect(
    getGridLayoutMode(900, { responsiveEnabled: false, editMode: false }),
  ).toBe('standard');
  expect(
    getGridLayoutMode(1600, { responsiveEnabled: false, editMode: false }),
  ).toBe('standard');
});

test('returns standard at and above the compact breakpoint', () => {
  expect(
    getGridLayoutMode(DASHBOARD_GRID_COMPACT_BREAKPOINT, {
      responsiveEnabled: true,
      editMode: false,
    }),
  ).toBe('standard');
  expect(
    getGridLayoutMode(1920, { responsiveEnabled: true, editMode: false }),
  ).toBe('standard');
});

test('returns compact between the stack and compact breakpoints', () => {
  expect(
    getGridLayoutMode(DASHBOARD_GRID_STACK_BREAKPOINT, {
      responsiveEnabled: true,
      editMode: false,
    }),
  ).toBe('compact');
  expect(
    getGridLayoutMode(DASHBOARD_GRID_COMPACT_BREAKPOINT - 1, {
      responsiveEnabled: true,
      editMode: false,
    }),
  ).toBe('compact');
});

test('returns stack below the stack breakpoint', () => {
  expect(
    getGridLayoutMode(DASHBOARD_GRID_STACK_BREAKPOINT - 1, {
      responsiveEnabled: true,
      editMode: false,
    }),
  ).toBe('stack');
  expect(
    getGridLayoutMode(320, { responsiveEnabled: true, editMode: false }),
  ).toBe('stack');
});

test('returns standard in edit mode even below the stack breakpoint', () => {
  expect(
    getGridLayoutMode(400, { responsiveEnabled: true, editMode: true }),
  ).toBe('standard');
  expect(
    getGridLayoutMode(900, { responsiveEnabled: true, editMode: true }),
  ).toBe('standard');
});

test('returns standard before the container width is measured', () => {
  expect(
    getGridLayoutMode(0, { responsiveEnabled: true, editMode: false }),
  ).toBe('standard');
});
