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
import { recommendVizTypes } from './recommendViz';

test('recommends big number for one measure and no dimensions', () => {
  const recs = recommendVizTypes(1, 0);
  expect(recs[0].vizType).toBe(VizType.BigNumberTotal);
});

test('recommends bar or pie when measure plus categories', () => {
  const recs = recommendVizTypes(1, 1);
  expect(recs.map(r => r.vizType)).toEqual(
    expect.arrayContaining([VizType.Bar, VizType.Pie]),
  );
});

test('respects limit', () => {
  expect(recommendVizTypes(2, 2, 2)).toHaveLength(2);
});

test('returns empty-ish list when nothing selected but never throws', () => {
  const recs = recommendVizTypes(0, 0);
  expect(Array.isArray(recs)).toBe(true);
});
