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
import { planStarterCharts } from './starterDashboard';

test('plans big number and table at minimum', () => {
  const plans = planStarterCharts({
    id: 7,
    table_name: 'orders',
    metrics: [{ metric_name: 'count' }],
    columns: [{ column_name: 'status' }],
  });
  expect(plans.length).toBeGreaterThanOrEqual(2);
  expect(plans[0].viz_type).toBe(VizType.BigNumberTotal);
  expect(plans[1].viz_type).toBe(VizType.Table);
  expect(plans.some(p => p.viz_type === VizType.Bar)).toBe(true);
});

test('uses time series when no dimensions', () => {
  const plans = planStarterCharts({
    id: 1,
    table_name: 'events',
    metrics: [{ metric_name: 'count' }],
    columns: [{ column_name: 'ts', is_dttm: true }],
  });
  expect(plans.some(p => p.viz_type === VizType.Line)).toBe(true);
});
