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
import { VizType } from '@superset-ui/core';
import {
  CURATED_VIZ_TYPES,
  isCuratedVizType,
  orderCuratedVizEntries,
} from './curatedVizTypes';

test('curated list includes core consumer chart types', () => {
  expect(CURATED_VIZ_TYPES).toContain(VizType.Table);
  expect(CURATED_VIZ_TYPES).toContain(VizType.Bar);
  expect(CURATED_VIZ_TYPES).toContain(VizType.Line);
  expect(CURATED_VIZ_TYPES).toContain(VizType.Pie);
});

test('isCuratedVizType matches list membership', () => {
  expect(isCuratedVizType(VizType.Table)).toBe(true);
  expect(isCuratedVizType('not_a_real_viz')).toBe(false);
  expect(isCuratedVizType(null)).toBe(false);
});

test('orderCuratedVizEntries keeps curated order and injects selected long-tail', () => {
  const entries = [
    { key: VizType.Pie },
    { key: VizType.Table },
    { key: 'chord' },
    { key: VizType.Bar },
  ];
  const ordered = orderCuratedVizEntries(entries, 'chord');
  expect(ordered.map(e => e.key)).toEqual([
    'chord',
    VizType.Table,
    VizType.Bar,
    VizType.Pie,
  ]);
});

test('orderCuratedVizEntries omits missing curated keys', () => {
  const entries = [{ key: VizType.Table }, { key: VizType.Pie }];
  expect(orderCuratedVizEntries(entries, null).map(e => e.key)).toEqual([
    VizType.Table,
    VizType.Pie,
  ]);
});

test('orderCuratedVizEntries does not duplicate selected curated type', () => {
  const entries = [{ key: VizType.Table }, { key: VizType.Pie }];
  expect(
    orderCuratedVizEntries(entries, VizType.Table).map(e => e.key),
  ).toEqual([VizType.Table, VizType.Pie]);
});
