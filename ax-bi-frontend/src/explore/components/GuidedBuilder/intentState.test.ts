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
  initialGuidedIntent,
  nextGuidedIntentOnFormDataChange,
} from './intentState';
import { DEFAULT_GUIDED_VIZ_TYPE } from './vizDescriptors';
import { GuidedIntent } from './types';

const emptyIntent = (vizType: string): GuidedIntent => ({
  vizType,
  measures: [],
  dimensions: [],
  filters: [],
});

test('initialGuidedIntent falls back to default for missing viz_type', () => {
  const intent = initialGuidedIntent({});
  expect(intent.vizType).toBe(DEFAULT_GUIDED_VIZ_TYPE);
});

test('initialGuidedIntent falls back to default for unsupported viz_type', () => {
  const intent = initialGuidedIntent({ viz_type: 'chord' });
  expect(intent.vizType).toBe(DEFAULT_GUIDED_VIZ_TYPE);
});

test('initialGuidedIntent keeps supported viz and measures', () => {
  const intent = initialGuidedIntent({
    viz_type: VizType.Pie,
    metric: 'sum__num',
    groupby: ['country'],
  });
  expect(intent.vizType).toBe(VizType.Pie);
  expect(intent.measures).toEqual(['sum__num']);
  expect(intent.dimensions).toEqual(['country']);
});

test('nextGuidedIntentOnFormDataChange returns prev when type unchanged', () => {
  const prev = emptyIntent(VizType.Table);
  prev.measures = ['m1'];
  const next = nextGuidedIntentOnFormDataChange(prev, {
    viz_type: VizType.Table,
    metrics: ['other'],
  });
  expect(next).toBe(prev);
  expect(next.measures).toEqual(['m1']);
});

test('nextGuidedIntentOnFormDataChange returns prev for unsupported next type', () => {
  const prev = emptyIntent(VizType.Bar);
  const next = nextGuidedIntentOnFormDataChange(prev, {
    viz_type: 'chord',
  });
  expect(next).toBe(prev);
});

test('nextGuidedIntentOnFormDataChange resyncs when supported viz changes', () => {
  const prev = emptyIntent(VizType.Table);
  const next = nextGuidedIntentOnFormDataChange(prev, {
    viz_type: VizType.Pie,
    metric: 'sum__num',
    groupby: ['region'],
  });
  expect(next).not.toBe(prev);
  expect(next.vizType).toBe(VizType.Pie);
  expect(next.measures).toEqual(['sum__num']);
  expect(next.dimensions).toEqual(['region']);
});
